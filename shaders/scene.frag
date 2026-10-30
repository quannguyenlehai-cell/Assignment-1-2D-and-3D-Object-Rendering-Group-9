#version 330 core
in vec3 view_position;
in vec3 view_normal;
in vec3 vertex_color;
in vec3 gouraud_front;
in vec3 gouraud_back;
in vec2 uv;
uniform vec3 base_color, light_position;
uniform float shininess, ambient_strength;
uniform int mode;
uniform bool use_vertex_colors;
uniform sampler2D image_texture;
out vec4 frag_color;

void main() {
    // Assignment's flat COLOR means one uniform color, without lighting.
    if (mode == 0 || mode == 4) { frag_color=vec4(base_color,1.0); return; }
    if (mode == 1) {
        frag_color=vec4(gl_FrontFacing ? gouraud_front : gouraud_back,1.0); return;
    }
    if (mode == 5) { frag_color=vec4(vertex_color,1.0); return; }
    vec3 albedo = use_vertex_colors ? vertex_color : base_color;
    if (mode == 3) albedo=texture(image_texture,uv).rgb;
    // Phong computes lighting for every fragment using interpolated normals.
    vec3 N=normalize(view_normal);
    if (!gl_FrontFacing) N=-N;
    vec3 L=normalize(light_position-view_position);
    vec3 V=normalize(-view_position);
    float diffuse=max(dot(N,L),0.0);
    float specular=diffuse>0.0 ? pow(max(dot(reflect(-L,N),V),0.0),shininess) : 0.0;
    frag_color=vec4(albedo*(ambient_strength+0.75*diffuse)+vec3(0.4*specular),1.0);
}
