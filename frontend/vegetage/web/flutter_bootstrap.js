{{flutter_js}}
{{flutter_build_config}}

// CanvasKit を gstatic CDN でなく同梱版(build/web/canvaskit/)から読む
_flutter.loader.load({
  config: {
    canvasKitBaseUrl: "canvaskit/",
  },
});
