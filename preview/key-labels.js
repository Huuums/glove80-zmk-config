// Shared by the web viewer and native overlay.
const symbols={SPACE:'Space',BSPC:'⌫',BACKSPACE:'⌫',DELETE:'Del',DEL:'Del',ENTER:'Enter',RET:'Enter',ESC:'Esc',TAB:'Tab',UP:'↑',DOWN:'↓',LEFT:'←',RIGHT:'→',PG_UP:'PgUp',PG_DN:'PgDn',MINUS:'−',EQUAL:'=',SQT:"'",SEMI:';',COMMA:',',DOT:'.',FSLH:'/',BSLH:'\\',LBKT:'[',RBKT:']',GRAVE:'`',LSHFT:'Shift',LSFT:'Shift',RSHFT:'Shift',RSHIFT:'Shift',LCTRL:'Ctrl',RCTRL:'Ctrl',LALT:'Alt',RALT:'Alt',LGUI:'Super',RGUI:'Super'};
const icons={'fa-align-left':'⇤','fa-align-right':'⇥','fa-circle':'●','tb-circle-dot':'⊙','fa-circle-dot':'⊙','fa-angle-double-up':'⇈','fa-angle-double-down':'⇊','fa-angle-double-left':'⇇','fa-angle-double-right':'⇉','tb-numbers':'123','tb-world':'◎','fa-alarm-clock':'◷','tb-variable-plus':'ƒ','fa-ankh':'☥','fa-cut':'✂','fa-undo':'↶','fa-redo':'↷','fa-copy':'▣','fa-paste':'▤','fa-code':'‹›','fa-circle-check':'✓','fa-minus':'−','fa-search':'⌕','fa-search-minus':'−','fa-search-plus':'+','fa-adjust':'◐','fa-folder':'▱','fa-bolt':'ϟ','fa-power-off':'⏻','tb-music':'♫','fa-equals':'=','fa-a':'A','fa-b':'B','fa-0':'0','fa-1':'1','fa-2':'2','fa-3':'3','tb-activity':'∿','tb-spiral':'↻','tb-icons':'▦','io-finger-print':'◉','fa-asl-interpreting':'↔','fa-shield-blank':'◇','di-linux':'L','fa-wand-magic-sparkles':'✧','fa-quidditch-broom-ball':'✦'};
function parameter(p) {return p.value+(p.params?.length?'('+p.params.map(parameter).join(', ')+')':'');}
function binding(key) {const params=(key.params||[]).map(parameter).join(' ');return key.value==='Custom'?params:[key.value,params].filter(Boolean).join(' ');}
const shiftedCharacters={'1':'!','2':'@','3':'#','4':'$','5':'%','6':'^','7':'&','8':'*','9':'(','0':')','-':'_','=':'+','[':'{',']':'}','\\':'|',';':':',"'":'"',',':'<','.':'>','/':'?','`':'~'};
Object.assign(symbols,{MINUS:'-',INS:'Ins',EXCL:'!',EXCLAMATION:'!',AT:'@',AT_SIGN:'@',HASH:'#',DLLR:'$',DOLLAR:'$',PRCNT:'%',PERCENT:'%',CARET:'^',AMPS:'&',AMPERSAND:'&',STAR:'*',ASTERISK:'*',LPAR:'(',RPAR:')',UNDER:'_',UNDERSCORE:'_',PLUS:'+',LBRC:'{',RBRC:'}',PIPE:'|',COLON:':',DQT:'"',DOUBLE_QUOTES:'"',LT:'<',GT:'>',QMARK:'?',QUESTION:'?',TILDE:'~'});
function pretty(value) {
  const shift=value.match(/^(?:LS|RS)\((.*)\)$/i);
  if(shift) {
    const base=pretty(shift[1]);
    if(shiftedCharacters[base])return shiftedCharacters[base];
    if(/^[a-z]$/i.test(base))return base.toUpperCase();
    return 'Shift + '+base;
  }
  const normalized=value.toUpperCase();
  return symbols[normalized]||(/^N[0-9]$/.test(normalized)?normalized.slice(1):value);
}
function shiftedLabel(text, mods) {
  if(!(mods&0x22))return text;
  return shiftedCharacters[text] || (/^[a-z]$/i.test(text)?text.toUpperCase():text);
}
function hidLabel(encoded, held=0) {
  if(encoded===0)return '';
  const usage=encoded&0xffff, page=(encoded>>>16)&0xff;
  if(page!==7)return 'HID '+encoded.toString(16);
  const mods=(encoded>>>24)|held;
  let text=usage>=4&&usage<=29?String.fromCharCode(65+usage-4):usage>=30&&usage<=38?String(usage-29):usage===39?'0':null;
  const names={40:'Enter',41:'Esc',42:'⌫',43:'Tab',44:'Space',45:'-',46:'=',47:'[',48:']',49:'\\',51:';',52:"'",53:'`',54:',',55:'.',56:'/',73:'Ins',74:'Home',75:'PgUp',76:'Del',77:'End',78:'PgDn',79:'→',80:'←',81:'↓',82:'↑',224:'Ctrl',225:'Shift',226:'Alt',227:'Super',228:'Ctrl',229:'Shift',230:'Alt',231:'Super'};
  text=text||names[usage]||(usage>=58&&usage<=69?'F'+(usage-57):'HID '+usage.toString(16));
  text=shiftedLabel(text,mods);
  const prefix=[];
  if(mods&0x11)prefix.push('Ctrl');if(mods&0x44)prefix.push('Alt');if(mods&0x88)prefix.push('Super');
  return [...prefix,text].join(' + ');
}
function label(key) {
  const held=connected?(liveModifiers||0):0;
  if(key.resolved)return key.resolved.codes.map(code=>hidLabel(code,key.resolved.clearsModifiers?0:held)).filter(Boolean).join(' → ')||'—';if(key.decoration?.label)return shiftedLabel(key.decoration.label,held);const b=binding(key);if(b==='&none')return '—';if(b==='&trans')return '▽';if(key.value==='&kp')return shiftedLabel(pretty(key.params?.[0]?parameter(key.params[0]):''),held);return b.replace(/^&/,'');}
