{ lib, python }:
python.pkgs.buildPythonPackage rec {
  pname = "sfconn";
  version = "0.2.3";
  src = ./.;

  propagatedBuildInputs = with python.pkgs; [
    snowflake-connector-python
  ];

  doCheck = false;

  meta = with lib; {
    homepage = "https://github.com/padhia/sfconn";
    description = "Snowflake connection helper functions";
    maintainers = with maintainers; [ padhia ];
  };
}
