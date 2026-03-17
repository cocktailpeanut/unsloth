module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        venv: "../../../env",
        venv_python: "3.12",
        env: {
          HOME: "{{path.resolve(cwd, 'app')}}",
          USERPROFILE: "{{path.resolve(cwd, 'app')}}"
        },
        path: "app/studio/backend",
        message: [
          "python run.py --host 127.0.0.1 --port {{port}}"
        ],
        on: [{
          event: "/(http:\\/\\/[^\\s]+)/",
          done: true
        }]
      }
    },
    {
      method: "local.set",
      params: {
        url: "{{input.event[1]}}"
      }
    }
  ]
}
