const studioEnv = {
  HOME: "{{path.resolve(cwd, 'app')}}",
  USERPROFILE: "{{path.resolve(cwd, 'app')}}"
}

module.exports = {
  run: [
    {
      when: "{{!exists('app')}}",
      method: "shell.run",
      params: {
        message: [
          "git clone https://github.com/unslothai/unsloth app",
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        env: studioEnv,
        path: "app/studio/frontend",
        message: [
          "npm install",
          "npm exec vite build"
        ]
      }
    },
    {
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
      when: "{{exists('app/studio/frontend/node_modules')}}",
      method: "fs.rm",
      params: {
        path: "app/studio/frontend/node_modules"
      }
    },
    {
      when: "{{exists('app/env')}}",
      method: "fs.rm",
      params: {
        path: "app/env"
      }
    },
    {
      when: "{{exists('app/unsloth.egg-info')}}",
      method: "fs.rm",
      params: {
        path: "app/unsloth.egg-info"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "../env",
        venv_python: "3.12",
        env: studioEnv,
        path: "app",
        message: [
          "python -m ensurepip --upgrade",
          "python studio/install_python_stack.py",
          "uv pip install -e ."
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "../env",
        venv_python: "3.12",
        env: studioEnv,
        path: "app",
        message: [
          "python ../build_llama_cpp.py --skip-if-present"
        ]
      }
    }
  ]
}
