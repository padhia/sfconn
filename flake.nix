{
  description = "Snowflake connection helper functions";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";

    nix-utils.url = "github:padhia/nix-utils";
    nix-utils.inputs.nixpkgs.follows = "nixpkgs";

    snowflake.url = "github:padhia/snowflake";
    snowflake.inputs = {
      nixpkgs.follows = "nixpkgs";
      flake-utils.follows = "flake-utils";
    };
  };

  outputs = { self, nixpkgs, nix-utils, flake-utils, snowflake }:
  let
    inherit (nix-utils.lib) pyDevShell extendPyPkgsWith;

    overlays.default = final: prev:
      extendPyPkgsWith prev {
        sfconn = ./sfconn.nix;
        sfconn02x = ./sfconn02x.nix;
      };

    buildSystem = system:
    let
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
        overlays = [ snowflake.overlays.default self.overlays.default ];
      };
    in {
      devShells.default = pyDevShell {
        inherit pkgs;
        name = "sfconn";
        extra = [ "snowflake-snowpark-python" ];
        pyVer = "311";
      };
    };

  in {
    inherit overlays;
    inherit (flake-utils.lib.eachDefaultSystem buildSystem) devShells;
  };
}
