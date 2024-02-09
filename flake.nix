{
  description = "Snowflake connection helper functions";

  inputs = {
    nixpkgs.url     = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    snowflake.url   = "github:padhia/snowflake";

    flake-utils.inputs.nixpkgs.follows = "nixpkgs";
    snowflake.inputs.nixpkgs.follows   = "nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils, snowflake }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs        = import nixpkgs { inherit system; };
        python3     = pkgs.python311;
        callPackage = pkgs.lib.callPackageWith (pkgs // python3.pkgs // pyPkgs);
        pyPkgs      = snowflake.pyPkgs { inherit pkgs python3; };

      in {
        packages.default = callPackage ./sfconn.nix {};

        devShells.default = pkgs.mkShell {
          name        = "sfconn";
          venvDir     = "./.venv";
          buildInputs = with pkgs.python311Packages; [
            python
            venvShellHook
            build
            pytest
            pyPkgs.snowflake-connector-python
            pkgs.ruff
          ];
        };
      }
    );
}
