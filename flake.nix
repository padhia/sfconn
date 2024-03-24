{
  description = "Snowflake connection helper functions";

  inputs = {
    nixpkgs.url   = "github:nixos/nixpkgs/nixos-unstable";
    nix-utils.url = "github:padhia/nix-utils";
    snowflake.url = "github:padhia/snowflake/next";

    nix-utils.inputs.nixpkgs.follows = "nixpkgs";
    snowflake.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, nix-utils, snowflake }:
    nix-utils.lib.mkPyFlake {
      pkgs       = { sfconn = import ./sfconn.nix; sfconn02x = import ./sfconn02x.nix; };
      defaultPkg = "sfconn";
      deps       = [ "snowflake-connector-python" "snowflake-snowpark-python" "pyjwt" "pytest" ];
      pyFlakes   = [ snowflake ];
    };
}
