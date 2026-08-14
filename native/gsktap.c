/* gsktap — LD_PRELOAD shim that taps a GTK4 app's render-node tree.
 *
 * Hooks gsk_renderer_render(); before forwarding to the real renderer, it
 * serializes the frame's GskRenderNode tree (the toolkit's scene description,
 * one step before rasterization) to $GSK_TAP_DIR/frame-NNNN.node.
 *
 * Build:  gcc -shared -fPIC -O2 -o gsktap.so gsktap.c -ldl
 * Run:    GSK_TAP_DIR=/tmp/tap LD_PRELOAD=./gsktap.so gtk4-widget-factory
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef void (*render_fn)(void *renderer, void *root, const void *region);

/* resolved from the process's own libgtk at runtime */
extern void *gsk_render_node_serialize(void *node);
extern const void *g_bytes_get_data(void *bytes, size_t *size);
extern void g_bytes_unref(void *bytes);

static render_fn real_render = NULL;
static int frame = 0;

void gsk_renderer_render(void *renderer, void *root, const void *region)
{
    if (!real_render)
        real_render = (render_fn) dlsym(RTLD_NEXT, "gsk_renderer_render");

    const char *dir = getenv("GSK_TAP_DIR");
    int max = getenv("GSK_TAP_MAX") ? atoi(getenv("GSK_TAP_MAX")) : 50;
    if (dir && frame < max) {
        void *bytes = gsk_render_node_serialize(root);
        if (bytes) {
            size_t len = 0;
            const char *data = g_bytes_get_data(bytes, &len);
            char path[512];
            snprintf(path, sizeof path, "%s/frame-%04d.node", dir, frame);
            FILE *f = fopen(path, "wb");
            if (f) { fwrite(data, 1, len, f); fclose(f); }
            g_bytes_unref(bytes);
        }
        frame++;
    }
    real_render(renderer, root, region);
}
