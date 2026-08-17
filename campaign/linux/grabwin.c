/* grabwin — the Linux per-window capture primitive (macOS/Windows rule, X11 impl).
 * Captures BOTH a window's own redirected surface (XCompositeNameWindowPixmap)
 * and the screen crop at the same geometry, so the two can be compared.
 * Usage: grabwin <window-id> <out-prefix>   -> writes <p>-window.ppm, <p>-screen.ppm
 */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/extensions/Xcomposite.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static void dump_ppm(const char *path, XImage *img) {
  FILE *f = fopen(path, "wb");
  fprintf(f, "P6\n%d %d\n255\n", img->width, img->height);
  for (int y = 0; y < img->height; y++)
    for (int x = 0; x < img->width; x++) {
      unsigned long p = XGetPixel(img, x, y);
      unsigned char rgb[3] = { (p >> 16) & 0xff, (p >> 8) & 0xff, p & 0xff };
      fwrite(rgb, 1, 3, f);
    }
  fclose(f);
}

int main(int argc, char **argv) {
  if (argc < 3) { fprintf(stderr, "usage: grabwin <winid> <out-prefix>\n"); return 2; }
  Window w = (Window)strtoul(argv[1], NULL, 0);
  Display *d = XOpenDisplay(NULL);
  if (!d) { fprintf(stderr, "no display\n"); return 2; }

  int ev, err, maj = 0, min = 0;
  if (!XCompositeQueryExtension(d, &ev, &err)) {
    printf("COMPOSITE_ABSENT\n"); return 1;      /* the signature datum either way */
  }
  XCompositeQueryVersion(d, &maj, &min);
  printf("composite=%d.%d\n", maj, min);

  XWindowAttributes a;
  XGetWindowAttributes(d, w, &a);
  int rx, ry; Window child;
  XTranslateCoordinates(d, w, a.root, 0, 0, &rx, &ry, &child);
  printf("geom=%d,%d,%dx%d\n", rx, ry, a.width, a.height);

  /* 1. the window's OWN surface: redirect -> offscreen pixmap -> read it */
  XCompositeRedirectWindow(d, w, CompositeRedirectAutomatic);
  XSync(d, False);
  /* force a repaint so the fresh offscreen pixmap holds real content */
  XClearArea(d, w, 0, 0, 0, 0, True);
  XSync(d, False);
  usleep(600 * 1000);
  Pixmap pm = XCompositeNameWindowPixmap(d, w);
  XImage *wi = XGetImage(d, pm, 0, 0, a.width, a.height, AllPlanes, ZPixmap);
  char path[1024];
  snprintf(path, sizeof path, "%s-window.ppm", argv[2]);
  dump_ppm(path, wi);

  /* 2. the screen crop at the same rect (what a naive guard would read) */
  XImage *si = XGetImage(d, a.root, rx, ry, a.width, a.height, AllPlanes, ZPixmap);
  snprintf(path, sizeof path, "%s-screen.ppm", argv[2]);
  dump_ppm(path, si);

  XCompositeUnredirectWindow(d, w, CompositeRedirectAutomatic);
  printf("OK\n");
  return 0;
}
