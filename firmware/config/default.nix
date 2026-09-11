{ firmware ? import ../src {} }:
let
  build = board: firmware.zmk.override {
    inherit board;
    keymap = ./glove80.keymap;
    kconfig = ./glove80.conf;
  };
in firmware.combine_uf2 (build "glove80_lh") (build "glove80_rh")
