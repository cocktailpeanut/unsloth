const studioEnv = {
  HOME: "{{path.resolve(cwd, 'app')}}",
  USERPROFILE: "{{path.resolve(cwd, 'app')}}"
}

module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        message: "git pull"
      }
    },
    {
    when: "{{exists('app')}}",
    method: "shell.run",
    params: {
      env: studioEnv,
      path: "app",
      message: "git pull"
    }
  },
  {
    when: "{{exists('app')}}",
    method: "shell.run",
    params: {
      env: studioEnv,
      path: "app/studio/frontend",
      message: [
        "npm install",
        "npm run build"
      ]
    }
  },
  {
    when: "{{exists('app')}}",
    method: "shell.run",
    params: {
      env: studioEnv,
      path: "app/studio/backend/core/data_recipe/oxc-validator",
      message: [
        "npm install"
      ]
    }
  },
  {
    when: "{{exists('app')}}",
    method: "shell.run",
    params: {
      venv: "env",
      venv_python: "3.12",
      env: studioEnv,
      path: "app",
      message: [
        "python studio/install_python_stack.py",
        "uv pip install -e ."
      ]
    }
  },
  {
    when: "{{exists('app')}}",
    method: "shell.run",
    params: {
      venv: "env",
      venv_python: "3.12",
      env: studioEnv,
      path: "app",
      message: [
        "python ../build_llama_cpp.py --refresh"
      ]
    }
  }
  ]
}
