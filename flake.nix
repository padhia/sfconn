{
  description = "Snowflake connection helper functions";

  inputs = {
    nixpkgs.url     = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    snowflake.url   = "github:padhia/snowflake";
    snowflake.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils, snowflake }:
  flake-utils.lib.eachDefaultSystem (system:
  let
    pkgs    = nixpkgs.legacyPackages.${system};
    pythons = ["python311" "python312"];
    python3 = pkgs.lib.replaceStrings ["."] [""] pkgs.python3.libPrefix;

    pyPkgsDep = py: {
      inherit (snowflake.packages.${system}.${"${py}Packages"}) snowflake-connector-python;
    };

    pyPkgs = py:
      let
        callPackage = pkgs.lib.callPackageWith (pkgs.${py}.pkgs // (pyPkgsDep py));
      in {
        sfconn    = callPackage ./sfconn.nix {};
        sfconn02x = callPackage ./sfconn02x.nix {};
       };

    devShells =
      let
        mkDevShell = py:
          pkgs.mkShell {
            name = "sfconn";
            venvDir = "./.venv";
            buildInputs = with pkgs.${py}.pkgs; [
              pkgs.${py}
              pkgs.ruff
              venvShellHook
              build
              pytest
              (pyPkgsDep py).snowflake-connector-python
            ];
          };

        allPys = pkgs.lib.genAttrs pythons mkDevShell;

      in
        allPys // { default = allPys.${python3}; };

    packages = with pkgs.lib;
      let
        allPys  = genAttrs pythons pyPkgs;
        allPkgs = mapAttrs' (k: v: nameValuePair (k + "Packages") v) allPys;
      in
        allPkgs // { default = allPkgs.${python3 + "Packages"}.sfconn; };

  in {
    inherit devShells packages;
  });
}
