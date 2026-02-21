FROM node:20-alpine

WORKDIR /front

# Instala deps primero (mejor cache)
COPY package.json package-lock.json* ./
RUN npm install

# Copia el resto
COPY . .

EXPOSE 5173

# Sync deps when package.json changes (e.g. after adding Tailwind/Shadcn)
# when using a mounted node_modules volume
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0 --port 5173"]