"""Static maintenance page served while the data pipeline is being rebuilt."""

PAGE = """<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Prumo — Em manutenção</title>
<link rel="icon" type="image/svg+xml" href="/static/images/prumo/favicon.svg">
<style>
  body { margin: 0; min-height: 100vh; display: flex; align-items: center;
         justify-content: center; font-family: system-ui, sans-serif;
         background: #f7f5f0; color: #1d2a33; text-align: center; }
  main { padding: 2rem; max-width: 32rem; }
  h1 { font-size: 2rem; margin: 1rem 0 .5rem; }
  p { color: #55636d; line-height: 1.5; }
  img { width: 64px; height: 64px; }
</style>
</head>
<body>
<main>
  <img src="/static/images/prumo/favicon.svg" alt="Prumo">
  <h1>Em manutenção</h1>
  <p>O Prumo está a ser reconstruído. Voltamos em breve.</p>
</main>
</body>
</html>
"""
