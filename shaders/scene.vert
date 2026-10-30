#version 330 core
// Match the VBO attribute locations in rendering.py.
layout(location=0) in vec3 position;
layout(location=1) in vec3 color;
layout(location=2) in vec3 normal;
layout(location=3) in vec2 texcoord;

uniform mat4 projection, view, model;
uniform mat3 normal_matrix; // inverse transpose of (view * model)'s 3x3 part
uniform vec3 base_color, light_position;
uniform float shininess, ambient_strength;
uniform bool use_vertex_colors;

out vec3 view_position;
out vec3 view_normal;
out vec3 vertex_color;
out vec3 gouraud_front;
out vec3 gouraud_back;
out vec2 uv;

vec3 lighting(vec3 p, vec3 n, vec3 albedo) {
    vec3 L = normalize(light_position-p);
    vec3 V = normalize(-p);
    float diffuse = max(dot(n, L), 0.0);
    float specular = diffuse > 0.0 ? pow(max(dot(reflect(-L,n),V),0.0),shininess) : 0.0;
    return albedo*(ambient_strength+0.75*diffuse)+vec3(0.4*specular);
}

void main() {
    vec4 p = view * model * vec4(position, 1.0);
    view_position = p.xyz;
    view_normal = normalize(normal_matrix*normal);
    vertex_color = color;
    uv = texcoord;
    vec3 albedo = use_vertex_colors ? color : base_color;
    // Gouraud computes lighting here, once per vertex; rasterizer interpolates it.
    gouraud_front = lighting(p.xyz, view_normal, albedo);
    gouraud_back = lighting(p.xyz, -view_normal, albedo);
    gl_Position = projection * p;
}
