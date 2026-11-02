FROM nginx:alpine

# Copy landing page and assets
COPY web/ /usr/share/nginx/html/

# Copy standalone executable for download
COPY AutoKeyClicker.exe /usr/share/nginx/html/

# Set proper permissions
RUN chmod -R 755 /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
