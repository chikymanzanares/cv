FROM node:20-alpine

WORKDIR /front

# Instala deps primero (mejor cache)
COPY package.json package-lock.json* ./
RUN npm install

# Copia el resto
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]