module.exports = {
  apps: [
    {
      name: "legacy-mint",
      script: "main.py",
      interpreter: "python3",
      watch: false,
      max_memory_restart: "200M",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      error_file: "logs/error.log",
      out_file: "logs/output.log",
    }
  ]
};