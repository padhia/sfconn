{
  lib,
  buildPythonPackage,
  setuptools,
  snowflake-connector-python,
  keyring,
  pyjwt,
}:
buildPythonPackage rec {
  pname = "sfconn";
  version = "0.3.3";
  pyproject = true;
  src = ./.;

  dependencies = [
    snowflake-connector-python
    keyring
    pyjwt
  ];

  build-system = [ setuptools ];
  doCheck = false;

  meta = with lib; {
    homepage    = "https://github.com/padhia/sfconn";
    description = "Snowflake connection helper functions";
    maintainers = with maintainers; [ padhia ];
  };
}
