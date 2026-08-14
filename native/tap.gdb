# gdb-based render-node tap (Plan B: libgtk is built -Bsymbolic, LD_PRELOAD can't
# interpose intra-library calls). Breaks on gsk_renderer_render, serializes the
# node tree in-process, dumps each frame to /tmp/tap/frame-NNNN.node.
set pagination off
set confirm off
set breakpoint pending on
set $i = 0
break gsk_renderer_render
commands 1
  silent
  set $node = (void*)$rsi
  set $bytes = (void*) gsk_render_node_serialize($node)
  set $szp = (unsigned long*) malloc(8)
  set $data = (char*) g_bytes_get_data($bytes, $szp)
  set $sz = *$szp
  eval "dump binary memory /tmp/tap/frame-%04d.node $data ($data + %lu)", $i, $sz
  call (void) g_bytes_unref($bytes)
  call (void) free($szp)
  set $i = $i + 1
  if $i >= 12
    call (void) exit(0)
  end
  continue
end
run
quit
