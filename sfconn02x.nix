{
  lib,
  buildPythonPackage,
  fetchPypi,
  setuptools,
  snowflake-connector-python,
  keyring,
  pyjwt,
}:
buildPythonPackage rec {
  pname = "sfconn";
  version = "0.2.5";
  pyproject = true;

  src = fetchPypi {
    inherit pname version;
    hash = "sha256-jdhR9UgHH2klrTtI0bSWN4/FSYXxJdlDhKMRW7c+AdQ=";
  };

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
