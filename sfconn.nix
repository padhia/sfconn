{ lib, buildPythonPackage, snowflake-connector-python }:

buildPythonPackage rec {
  pname = "sfconn";
  version = "0.2.4";
  src = ./.;

  propagatedBuildInputs = [
    snowflake-connector-python
  ];

  doCheck = false;

  meta = with lib; {
    homepage = "https://github.com/padhia/sfconn";
    description = "Snowflake connection helper functions";
    maintainers = with maintainers; [ padhia ];
  };
}
