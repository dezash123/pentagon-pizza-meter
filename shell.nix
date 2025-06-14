with import <nixpkgs> {};
mkShell {
  buildInputs = [
    python312
    python312Packages.pip
    python312Packages.virtualenv
    nodejs
  ] ++ (with python312Packages; [
    requests
    pydantic
    python-dotenv
    beautifulsoup4
    selenium
  ]);
  
  shellHook = ''
    VENV_DIR=".venv"
    
    if [ ! -d "$VENV_DIR" ]; then
      python -m venv $VENV_DIR
    fi
    
    source $VENV_DIR/bin/activate
    
    pip install --upgrade pip > /dev/null 2>&1
    
    pip install -r requirements.txt

    export PYTHONPATH="$PWD:$PYTHONPATH"
  '';

    exitHook = ''
    if [ -n "$VIRTUAL_ENV" ]; then
      deactivate
    fi
  '';
}
