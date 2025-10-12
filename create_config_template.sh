#!/bin/bash
# create_config_template.sh

cat > config.d/template.yml <<'EOF'
images:
  my-custom-image:
    image: myimage:latest
    shell: /bin/bash
    keep_alive_cmd: sleep infinity
    description: "My Custom Image"
    category: custom
    
    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Custom Image Quick Reference                 ║
      ╚══════════════════════════════════════════════════════════════╝
      
      Add your helpful commands here!
    
    scripts:
      post_start:
        inline: |
          #!/bin/bash
          CONTAINER_NAME="$1"
          echo "Initializing $CONTAINER_NAME..."
          # Your initialization commands here
      
      pre_stop:
        inline: |
          #!/bin/bash
          CONTAINER_NAME="$1"
          echo "Cleaning up $CONTAINER_NAME..."
          # Your cleanup commands here
EOF

echo "✓ Template created: config.d/template.yml"