{
  description = "Snowflake connection helper functions";

  inputs = {
    nixpkgs.url   = "github:nixos/nixpkgs/nixos-unstable";
    snowflake.url = "github:padhia/snowflake";
    snowflake.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils, snowflake }:
  let
    forAllSystems = fn:
      let
        systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      in
        nixpkgs.lib.genAttrs systems (system: fn (import nixpkgs { inherit system; }));

    pyPkgs = { pkgs, python3 }:
      let
        callPackage = pkgs.lib.callPackageWith (pkgs // python3.pkgs // allPyPkgs);
        allPyPkgs = (snowflake.pyPkgs { inherit pkgs python3; }) // { sfconn = callPackage ./sfconn.nix {}; };
      in { inherit (allPyPkgs) sfconn snowflake-connector-python; };

    devShells = forAllSystems( pkgs: with pkgs;
      let
        python3  = pkgs.python311;
        sfPyPkgs = pyPkgs { inherit pkgs python3; };

      in {
        default = pkgs.mkShell {
          name = "sfconn";
          venvDir = "./.venv";
          buildInputs = with pkgs.python311Packages; [
            python
            venvShellHook
            build
            pytest
            pkgs.ruff
            sfPyPkgs.snowflake-connector-python
          ];
        };
      }
    );

    packages = forAllSystems (pkgs: with pkgs;
      let
        default = (pyPkgs { inherit pkgs; python3 = python311; }).sfconn;
      in { inherit default; }
    );

  in {
    inherit devShells packages pyPkgs;
  };
}
