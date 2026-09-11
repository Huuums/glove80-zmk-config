/* SPDX-License-Identifier: MIT */
/* Read-only layer telemetry, compiled only into the left (central) half. */
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/ring_buffer.h>
#include <zmk/ble.h>
#include <zmk/keymap.h>
#include <zmk/hid.h>
#include <zmk/event_manager.h>
#include <zmk/events/layer_state_changed.h>

#define SERVICE_UUID BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(0x64d90001, 0x7e6b, 0x4f7e, 0x9c80, 0x2f7d773a4b10))
#define STATE_UUID BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(0x64d90002, 0x7e6b, 0x4f7e, 0x9c80, 0x2f7d773a4b10))
#define PACKET_SIZE 9

BUILD_ASSERT(ZMK_KEYMAP_LAYERS_LEN <= 32, "Telemetry supports up to 32 layers");
K_SEM_DEFINE(changed, 0, 1);
RING_BUF_DECLARE(usb_tx, 128);
static const struct device *const serial = DEVICE_DT_GET(DT_NODELABEL(layer_telemetry_uart));

static void snapshot(uint8_t packet[PACKET_SIZE]) {
    packet[0] = 'G';
    packet[1] = 'L';
    packet[2] = 2;
    packet[3] = ZMK_KEYMAP_LAYERS_LEN;
    uint32_t mask = zmk_keymap_layer_state() | BIT(zmk_keymap_layer_default());
    sys_put_le32(mask, &packet[4]);
    packet[8] = zmk_hid_get_keyboard_report()->body.modifiers;
}

// Called immediately after ZMK updates the effective HID modifier byte.
void zmk_layer_telemetry_modifiers_changed(void) { k_sem_give(&changed); }

static ssize_t read_state(struct bt_conn *conn, const struct bt_gatt_attr *attr,
                          void *buf, uint16_t len, uint16_t offset) {
    uint8_t packet[PACKET_SIZE];
    snapshot(packet);
    return bt_gatt_attr_read(conn, attr, buf, len, offset, packet, sizeof(packet));
}

static void subscription_changed(const struct bt_gatt_attr *attr, uint16_t value) {
    ARG_UNUSED(attr);
    ARG_UNUSED(value);
    k_sem_give(&changed);
}

BT_GATT_SERVICE_DEFINE(layer_service,
    BT_GATT_PRIMARY_SERVICE(SERVICE_UUID),
    BT_GATT_CHARACTERISTIC(STATE_UUID, BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ_ENCRYPT, read_state, NULL, NULL),
    BT_GATT_CCC(subscription_changed, BT_GATT_PERM_READ_ENCRYPT | BT_GATT_PERM_WRITE_ENCRYPT));

/* One producer (telemetry thread), one consumer (UART ISR). Never block the
 * keyboard event loop on a slow or disconnected host. Frames are all-or-none. */
static void serial_irq(const struct device *dev, void *user_data) {
    ARG_UNUSED(user_data);
    while (uart_irq_update(dev) && uart_irq_is_pending(dev)) {
        if (uart_irq_tx_ready(dev)) {
            uint8_t *data;
            uint32_t size = ring_buf_get_claim(&usb_tx, &data, PACKET_SIZE);
            if (!size) {
                uart_irq_tx_disable(dev);
                break;
            }
            int sent = uart_fifo_fill(dev, data, size);
            ring_buf_get_finish(&usb_tx, sent > 0 ? sent : 0);
            if (sent <= 0) { break; }
        } else { break; }
    }
}

static void telemetry_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    bool usb_ready = device_is_ready(serial) &&
                     uart_irq_callback_user_data_set(serial, serial_irq, NULL) == 0;
    for (;;) {
        uint8_t packet[PACKET_SIZE];
        snapshot(packet);
        struct bt_conn *conn = zmk_ble_active_profile_conn();
        if (conn) {
            if (bt_gatt_is_subscribed(conn, &layer_service.attrs[2], BT_GATT_CCC_NOTIFY)) {
                /* Failed sends are retried with the latest snapshot on heartbeat. */
                bt_gatt_notify(conn, &layer_service.attrs[2], packet, sizeof(packet));
            }
            bt_conn_unref(conn);
        }
        uint32_t dtr = 0;
        if (usb_ready && uart_line_ctrl_get(serial, UART_LINE_CTRL_DTR, &dtr) == 0 && dtr &&
            ring_buf_space_get(&usb_tx) >= sizeof(packet)) {
            ring_buf_put(&usb_tx, packet, sizeof(packet));
            uart_irq_tx_enable(serial);
        }
        /* Heartbeats give USB an initial snapshot, recover lost updates, and
         * allow the receiver to mark stale connections. No unbounded queue. */
        k_sem_take(&changed, K_SECONDS(1));
    }
}

static int layer_changed(const zmk_event_t *event) {
    ARG_UNUSED(event);
    k_sem_give(&changed);
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(layer_telemetry, layer_changed);
ZMK_SUBSCRIPTION(layer_telemetry, zmk_layer_state_changed);
K_THREAD_DEFINE(layer_telemetry_thread, 2048, telemetry_thread, NULL, NULL, NULL,
                K_LOWEST_APPLICATION_THREAD_PRIO, 0, 500);
