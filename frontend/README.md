# Frontend: Chatbot Archivo Patrimonial UAH

Este es el frontend de la plataforma, desarrollado con **Next.js 14**, **Tailwind CSS** y **Framer Motion**.

## 🚀 Cómo iniciar el frontend

### Opción A: Recomendada (Docker)
Si quieres iniciar el frontend junto con todo el backend (IA, Búsqueda, etc.), usa el comando en la raíz del proyecto:
```bash
docker compose up -d --build
```
El frontend estará disponible en: [http://localhost:8090](http://localhost:8090).

### Opción B: Desarrollo Local (Node.js)
Si solo quieres trabajar en el diseño del frontend:
1. Asegúrate de tener Node.js instalado.
2. Instala las dependencias:
   ```bash
   npm install
   ```
3. Inicia el servidor de desarrollo:
   ```bash
   npm run dev
   ```
El servidor de desarrollo correrá en [http://localhost:3000](http://localhost:3000).

---

## 🎨 Diseño y Estilos
*   Los estilos globales y colores institucionales están definidos en `src/app/globals.css`.
*   La lógica de la interfaz de chat se encuentra en `src/app/page.tsx`.
*   Se utiliza la tipografía **Playfair Display** para títulos y **Inter** para el cuerpo de texto.

---

**Para ver la guía completa del sistema, consulta el [README principal en la raíz del proyecto](../README.md).**
