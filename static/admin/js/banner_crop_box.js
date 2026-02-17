(function () {
  function byId(id) {
    return document.getElementById(id);
  }

  function intVal(input) {
    var n = parseInt(input && input.value ? input.value : "0", 10);
    return Number.isFinite(n) && n >= 0 ? n : 0;
  }

  function setVal(input, value) {
    if (input) input.value = String(Math.max(0, Math.round(value)));
  }

  function initCropTool() {
    var stage = byId("banner-crop-stage");
    var image = byId("banner-crop-image");
    var rect = byId("banner-crop-rect");
    if (!stage || !image || !rect) return;

    var fields = {
      desktop: {
        x: byId("id_desktop_crop_x"),
        y: byId("id_desktop_crop_y"),
        w: byId("id_desktop_crop_width"),
        h: byId("id_desktop_crop_height"),
      },
      mobile: {
        x: byId("id_mobile_crop_x"),
        y: byId("id_mobile_crop_y"),
        w: byId("id_mobile_crop_width"),
        h: byId("id_mobile_crop_height"),
      },
    };

    var mode = "desktop";
    var drag = null;

    function ratioX() {
      return image.naturalWidth / image.clientWidth;
    }

    function ratioY() {
      return image.naturalHeight / image.clientHeight;
    }

    function drawFromInputs() {
      var f = fields[mode];
      if (!f) return;

      var x = intVal(f.x);
      var y = intVal(f.y);
      var w = intVal(f.w);
      var h = intVal(f.h);
      if (!w || !h || !image.clientWidth || !image.clientHeight) {
        rect.style.display = "none";
        return;
      }

      rect.style.display = "block";
      rect.style.left = (x / ratioX()) + "px";
      rect.style.top = (y / ratioY()) + "px";
      rect.style.width = (w / ratioX()) + "px";
      rect.style.height = (h / ratioY()) + "px";
    }

    function writeInputs(displayX, displayY, displayW, displayH) {
      var f = fields[mode];
      if (!f) return;
      setVal(f.x, displayX * ratioX());
      setVal(f.y, displayY * ratioY());
      setVal(f.w, displayW * ratioX());
      setVal(f.h, displayH * ratioY());
      drawFromInputs();
    }

    function setMode(nextMode) {
      mode = nextMode;
      document.querySelectorAll("[data-crop-mode]").forEach(function (btn) {
        btn.classList.toggle("active", btn.getAttribute("data-crop-mode") === mode);
      });
      drawFromInputs();
    }

    stage.addEventListener("mousedown", function (evt) {
      if (evt.button !== 0) return;
      var bounds = image.getBoundingClientRect();
      var startX = Math.max(0, Math.min(bounds.width, evt.clientX - bounds.left));
      var startY = Math.max(0, Math.min(bounds.height, evt.clientY - bounds.top));
      drag = { startX: startX, startY: startY };
      evt.preventDefault();
    });

    window.addEventListener("mousemove", function (evt) {
      if (!drag) return;
      var bounds = image.getBoundingClientRect();
      var nowX = Math.max(0, Math.min(bounds.width, evt.clientX - bounds.left));
      var nowY = Math.max(0, Math.min(bounds.height, evt.clientY - bounds.top));
      var x = Math.min(drag.startX, nowX);
      var y = Math.min(drag.startY, nowY);
      var w = Math.abs(nowX - drag.startX);
      var h = Math.abs(nowY - drag.startY);
      rect.style.display = "block";
      rect.style.left = x + "px";
      rect.style.top = y + "px";
      rect.style.width = w + "px";
      rect.style.height = h + "px";
    });

    window.addEventListener("mouseup", function (evt) {
      if (!drag) return;
      var bounds = image.getBoundingClientRect();
      var nowX = Math.max(0, Math.min(bounds.width, evt.clientX - bounds.left));
      var nowY = Math.max(0, Math.min(bounds.height, evt.clientY - bounds.top));
      var x = Math.min(drag.startX, nowX);
      var y = Math.min(drag.startY, nowY);
      var w = Math.abs(nowX - drag.startX);
      var h = Math.abs(nowY - drag.startY);
      drag = null;
      writeInputs(x, y, w, h);
    });

    document.querySelectorAll("[data-crop-mode]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setMode(btn.getAttribute("data-crop-mode"));
      });
    });

    Object.keys(fields).forEach(function (name) {
      ["x", "y", "w", "h"].forEach(function (key) {
        var input = fields[name][key];
        if (input) {
          input.addEventListener("input", function () {
            if (name === mode) drawFromInputs();
          });
        }
      });
    });

    if (image.complete) {
      setMode("desktop");
    } else {
      image.addEventListener("load", function () {
        setMode("desktop");
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCropTool);
  } else {
    initCropTool();
  }
})();
