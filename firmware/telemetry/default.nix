{ firmware ? import ../src {}, side ? "combined" }:
let
  left = (firmware.zmk.override {
    board = "glove80_lh";
    keymap = builtins.toFile "telemetry.keymap"
      (builtins.readFile ../config/glove80.keymap + "\n" + builtins.readFile ./telemetry.keymap);
    kconfig = ./telemetry.conf;
  }).overrideAttrs (old: {
    postPatch = (old.postPatch or "") + ''
      # This ZMK version declares a modifier event but does not emit it.
      # Hook the report update instead, including masked and implicit modifiers.
      sed -i '1i void zmk_layer_telemetry_modifiers_changed(void);' src/hid.c
      substituteInPlace src/hid.c --replace-fail \
        'keyboard_report.body.modifiers = (mods & ~masked_modifiers) | implicit_modifiers;' \
        'keyboard_report.body.modifiers = (mods & ~masked_modifiers) | implicit_modifiers; zmk_layer_telemetry_modifiers_changed();'
      cp ${./layer_telemetry.c} src/layer_telemetry.c
      echo 'target_sources(app PRIVATE src/layer_telemetry.c)' >> CMakeLists.txt
    '';
  });
  right = firmware.zmk.override {
    board = "glove80_rh";
    keymap = ../config/glove80.keymap;
    kconfig = ../config/glove80.conf;
  };
in if side == "lh" then left else if side == "rh" then right
   else firmware.combine_uf2 left right
