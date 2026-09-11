"""Exercise the generated viewer in installed Brave, with simulated telemetry."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/brave', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1100})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    state = {'connected': True, 'layer_count': 32, 'layers': [0, 16, 31], 'transport': 'bluetooth'}
    page.route('http://viewer.test/', lambda route: route.fulfill(path=str(ROOT / 'preview/index.html'), content_type='text/html'))
    page.route('http://viewer.test/state', lambda route: route.fulfill(json=state))
    page.goto('http://viewer.test/')
    page.wait_for_function("document.getElementById('connection').textContent.includes('Connected')")
    assert page.locator('.key').count() == 80
    assert page.evaluate("parameter({value:'LS',params:[{value:'N1'}]})") == 'LS(N1)'
    assert page.locator('#layers button').count() == 32
    number = page.get_by_role('button', name='Preview layer 16: Number', exact=True)
    number.hover()
    assert page.locator('#view-name').inner_text() == 'Number'
    assert page.evaluate('displayedLayers()') == [16, 0]
    assert page.locator('#view-kind').text_content() == 'Hover preview'
    page.locator('h1').hover()
    assert page.evaluate('displayedLayers()') == [31, 16, 0]
    number.click()
    page.locator('h1').hover()
    assert page.locator('#view-kind').text_content() == 'Pinned preview'
    page.get_by_role('button', name='Preview layer 19: Symbol', exact=True).hover()
    assert page.evaluate('displayedLayers()') == [19, 16, 0]
    page.locator('h1').hover()
    assert page.locator('#view-name').inner_text() == 'Number'
    state['layers'] = [0, 15]
    page.wait_for_function("liveLayers.has(15)")
    assert page.locator('#view-name').inner_text() == 'Number'
    page.get_by_role('button', name='Follow keyboard', exact=True).click()
    assert page.evaluate('displayedLayers()') == [15, 0]
    # Helper output is derived from the compiled macro, not its 'Tap' decoration.
    assert page.evaluate('label(data.layers[6][34])') == 'C → B'
    state.update(layers=[0, 9], modifiers=2)
    page.wait_for_function('liveModifiers===2 && liveLayers.has(9)')
    assert page.evaluate('label(data.layers[9][39])') == 'E → -'
    assert page.evaluate("label({value:'&kp',params:[{value:'MINUS'}]})") == '_'
    assert page.locator('#modifier-state').inner_text() == '· Shift'
    assert page.evaluate('label(data.layers[5][35])') == 'C'
    state.update(layers=[0, 15], modifiers=0)
    page.wait_for_function('liveModifiers===0 && liveLayers.has(15)')
    assert page.evaluate("label({value:'&kp',params:[{value:'MINUS'}]})") == '-'
    pad = page.locator('#input-pad')
    pad.click()
    for binding, expected in [('LS(MINUS)', '_'), ('LS(N1)', '!'), ('RS(LBKT)', '{'), ('LS(SQT)', '\"'), ('LS(A)', 'A'), ('UNDER', '_')]:
        assert page.evaluate('(value)=>pretty(value)', binding) == expected
    for key, expected in [('-', '_'), ('_', '_'), ('1', '!'), ('!', '!'), ('A', 'A')]:
        page.evaluate('(key)=>document.dispatchEvent(new KeyboardEvent(\"keydown\",{key,shiftKey:true,bubbles:true}))', key)
        assert page.locator('#last-input').inner_text() == expected

    page.keyboard.press('a')
    assert page.locator('#last-input').inner_text() == 'a'
    page.keyboard.press('Control+k')
    assert page.locator('#last-input').inner_text() == 'Ctrl + k'
    state['layers'] = [0, 19]
    page.wait_for_function('liveLayers.has(19)')
    assert page.locator('#last-input').inner_text() == 'Ctrl + k'
    page.keyboard.insert_text('é')
    assert page.locator('#last-input').inner_text() == 'é'
    assert pad.input_value() == ''
    page.keyboard.press('Backspace')
    assert page.locator('#last-input').inner_text() == 'Backspace'
    page.get_by_role('button', name='Clear last input').click()
    assert page.locator('#last-input').inner_text() == '—'
    state['connected'] = False
    page.wait_for_function("document.getElementById('keyboard').style.opacity === '0.35'")
    number.hover()
    assert page.locator('#keyboard').evaluate('(el)=>el.style.opacity') == '1'
    assert page.locator('#view-name').inner_text() == 'Number'
    state.update(connected=True, layers=[0, 16])
    number.click()
    page.locator('h1').hover()
    page.wait_for_function('connected')
    page.screenshot(path='/tmp/glove80-viewer-brave.png', full_page=True)
    assert not errors, errors
    browser.close()
print('Brave passed: hover, pin, restore, live updates, layer precedence, keyboard shortcuts, text input, stale preview.')
