# Control de perfumes (Perfu Luxe)

1. Crear un repositorio en GitHub (público) y subir todo el contenido de esta carpeta a la rama `main`.
2. Settings > Pages > Source: Deploy from a branch > `main` / root.
3. Pestaña Actions > "Analizar Perfu Luxe" > Run workflow. Después de ~2 min aparecen los datos en `data/products.json`.
   Si falla, bajar el artefacto `debug` (captura y HTML de la página) y pasárselo a Claude para ajustar el lector.
4. Abrir `https://TU-USUARIO.github.io/NOMBRE-DEL-REPO/` e instalar: Chrome Android > menú > "Instalar app"; Chrome/Edge en Windows > ícono de instalar en la barra.
5. Se analiza solo los lunes a las 9:00. Para el botón "Analizar ahora": GitHub > Settings > Developer settings > Fine-grained token,
   solo para este repo, permiso Actions: Read and write. Pegarlo en la app (botón Margen). Queda guardado solo en ese dispositivo.
6. El margen (% o monto fijo) y el redondeo se cambian desde el botón Margen y se guardan en cada dispositivo.
