# Versionamiento con GitHub

## 1) Instala Git
Descarga e instala Git para Windows:
- https://git-scm.com/download/win

Verifica:
```powershell
git --version
```

## 2) Inicializa el repositorio local
Desde la carpeta del proyecto:
```powershell
git init
git add .
git commit -m "feat: base app Flask expotecnica con MVC, auth, evaluaciones y admin"
```

## 3) Crea el repositorio en GitHub
En GitHub crea un repo, por ejemplo: `expotecnica`.

## 4) Conecta remoto y sube
Reemplaza `TU_USUARIO` por tu usuario real:
```powershell
git branch -M main
git remote add origin https://github.com/TU_USUARIO/expotecnica.git
git push -u origin main
```

## 5) Flujo diario recomendado
```powershell
git status
git add .
git commit -m "descripcion corta del cambio"
git push
```

