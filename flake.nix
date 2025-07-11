{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    
    snowflake.url = "github:padhia/snowflake";
    snowflake.inputs = {
      nixpkgs.follows = "nixpkgs";
      flake-utils.follows = "flake-utils";
    };
  };

  outputs = { self, nixpkgs, flake-utils, snowflake }:
  let
    inherit (nixpkgs.lib) composeManyExtensions;

    pkgOverlay = final: prev: {
      pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
        (py-final: py-prev: {
          sfconn = py-final.callPackage ./sfconn.nix {};
          sfconn02x = py-final.callPackage ./sfconn02x.nix {};
        })
      ];
    };

    overlays.default = composeManyExtensions [
      snowflake.overlays.default
      pkgOverlay
    ];

    eachSystem = system:
    let
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
        overlays = [ self.overlays.default ];
      };

      pyPkgs = pkgs.python312Packages;

    in {
      devShells.default = pkgs.mkShell {
        name = "sfconn";
        venvDir = "./.venv";
        buildInputs = with pyPkgs; [
          pkgs.ruff
          pkgs.uv
          python
          venvShellHook
          pytest
          pyPkgs.snowflake-snowpark-python
        ];
      };
    };

  in {
    inherit overlays;
    inherit (flake-utils.lib.eachDefaultSystem eachSystem) devShells;
  };
}
