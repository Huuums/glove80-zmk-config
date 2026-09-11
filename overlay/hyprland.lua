-- Glove80 keyboard overlay: press Super+F8 to show or hide.
-- No keyboard focus is taken; typing continues in the current application.
hl.bind("SUPER + F8", hl.dsp.exec_cmd("gapplication action com.glove80.LayerOverlay toggle || /home/dennisc/.local/bin/glove80-overlay toggle"), { description = "Toggle Glove80 learning overlay" })
