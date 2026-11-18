/* Classic entry point: load vendor/three-atlas.js first. No fetch of model files. */
(() => {
  'use strict';

  // Eye directions, not rotations of the CAD. World XYZ = CAD (x, z, -y) in metres.
  const assemblyEye = [0.66, 0.54, 1];
  const groupEye = {
    Housing: assemblyEye,
    LowerBody: assemblyEye,
    Fascia: [0.18, 0.10, 1],
    LightRing: [0.5, 0.65, 1],
    Pod: [0.52, 0.86, 1],
    MainPCB: [-0.17, 0.11, -1],
    DisplayPCB: [0.18, 0.10, 1],
    Heater: [0.62, 0.95, 1],
    Battery: [0.56, 0.35, -1],
    Harness: [-0.54, 0.26, -1],
    Mounts: [0.72, 0.53, 1],
  };
  const upright = [0, 1, 0];
  const fixedViews = {
    front: { eye: [0, 0, 1], up: upright },
    back: { eye: [0, 0, -1], up: upright },
    left: { eye: [-1, 0, 0], up: upright },
    right: { eye: [1, 0, 0], up: upright },
    top: { eye: [0, 1, 0], up: [0, 0, -1] },
    bottom: { eye: [0, -1, 0], up: [0, 0, 1] },
  };
  const keyProfiles = new Set(['key-field', 'key-mark', 'bright-rim']);

  async function parseEmbeddedGLB(T, base64) {
    if (typeof base64 !== 'string' || !base64.length) {
      throw new Error('В данных атласа нет встроенного GLB.');
    }
    let bytes;
    if (typeof Uint8Array.fromBase64 === 'function') {
      bytes = Uint8Array.fromBase64(base64);
    } else {
      const binary = atob(base64);
      bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    }
    const header = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    if (bytes.length < 20 || header.getUint32(0, true) !== 0x46546c67 ||
        header.getUint32(4, true) !== 2 || header.getUint32(8, true) !== bytes.length) {
      throw new Error('Повреждён заголовок или размер GLB 2.0.');
    }
    const manager = new T.LoadingManager();
    manager.setURLModifier(url => {
      if (/^(blob:|data:)/i.test(url)) return url;
      throw new Error('Для этой модели требуется внешний ресурс; атлас рассчитан на автономный GLB.');
    });
    return new T.GLTFLoader(manager).parseAsync(bytes.buffer, '');
  }

  // Face the working surface of a physical key, not the generic front of its Housing
  // group. The glTF profile identifies the surface; its actual triangles give the tilt
  // (in particular on the sloping rear eject key). No change to the shape or material.
  function keyEye(T, part, assembly) {
    const sign = part.rest.min.z + part.rest.max.z < assembly.min.z + assembly.max.z ? -1 : 1;
    const sum = new T.Vector3();
    const a = new T.Vector3();
    const b = new T.Vector3();
    const c = new T.Vector3();
    for (const { mesh } of part.surfaces) {
      const { index, attributes } = mesh.geometry;
      const position = attributes.position;
      const count = index ? index.count : position.count;
      const vertex = (out, i) => out.fromBufferAttribute(position, index ? index.getX(i) : i).applyMatrix4(mesh.matrixWorld);
      for (let i = 0; i + 2 < count; i += 3) {
        vertex(a, i);
        vertex(b, i + 1);
        vertex(c, i + 2);
        const areaNormal = b.sub(a).cross(c.sub(a));
        if (sign * areaNormal.z > 0.55 * areaNormal.length()) sum.add(areaNormal);
      }
    }
    if (!sum.lengthSq()) sum.set(0, 0, sign);
    sum.normalize();
    return [sum.x + 0.14 * sign, sum.y + 0.09, sum.z];
  }

  function indexModel(T, gltf, data) {
    const source = gltf.parser.json.asset.extras?.sourceSHA256;
    if (source && data.sourceSHA256 && source !== data.sourceSHA256) {
      throw new Error('Каталог и GLB относятся к разным ревизиям CAD.');
    }
    const nodes = new Map();
    gltf.scene.updateMatrixWorld(true);
    gltf.scene.traverse(object => {
      // The loader sanitizes Object3D.name; use the original glTF node name for CAD identity.
      const index = gltf.parser.associations.get(object)?.nodes;
      if (index === undefined) return;
      const id = gltf.parser.json.nodes[index].name;
      if (!id) return;
      if (nodes.has(id)) throw new Error(`Повторяется узел glTF: ${id}.`);
      nodes.set(id, object);
    });

    const groups = new Map();
    for (const { id, explode } of data.groups) {
      const node = nodes.get(id);
      if (!node || !Array.isArray(explode) || explode.length !== 3 || !explode.every(Number.isFinite)) {
        throw new Error(`Нет узла или вектора разнесения для группы ${id}.`);
      }
      groups.set(id, { id, node, rest: node.position.clone(), delta: new T.Vector3(...explode) });
    }

    const parts = new Map();
    const owner = new WeakMap();
    const assembly = new T.Box3();
    for (const { id, group, explode } of data.parts) {
      const node = nodes.get(id);
      if (!node || !groups.has(group) || parts.has(id)) throw new Error(`Не сопоставлена деталь ${id}.`);
      const surfaces = [];
      node.traverse(mesh => {
        if (!mesh.isMesh) return;
        mesh.castShadow = true;
        owner.set(mesh, id);
        surfaces.push({ mesh, original: mesh.material });
      });
      const rest = new T.Box3().setFromObject(node);
      if (!surfaces.length || rest.isEmpty()) throw new Error(`В узле ${id} нет геометрии.`);
      assembly.union(rest);
      const g = groups.get(group);
      const delta = Array.isArray(explode) && explode.length === 3 && explode.every(Number.isFinite)
        ? new T.Vector3(...explode) : g.delta;
      parts.set(id, {
        id, group: g, node, surfaces, rest, delta, relative: delta.clone().sub(g.delta),
        origin: node.position.clone(), box: rest.clone(), variants: new Map(), eye: groupEye[group] || assemblyEye,
      });
    }
    if (!parts.size) throw new Error('Каталог деталей пуст.');
    for (const part of parts.values()) {
      const isKey = part.surfaces.some(({ original }) =>
        [].concat(original).some(material => keyProfiles.has(material.userData.visualProfile)));
      if (isKey) part.eye = keyEye(T, part, assembly);
    }
    return { groups, parts, owner };
  }

  // Catalog artwork is an optical state on the *existing* carrier's exterior faces.
  // Use the registered rest-frame in metres: exploding, staging or isolating the part
  // then moves the artwork with its vertices. No extra mesh/ID, UV rewrite or fetch.
  function makeScreen(T, model, lcd) {
    const carrier = model.parts.get(lcd?.anchor);
    const art = lcd?.artwork;
    const finite = (v, n) => Array.isArray(v) && v.length === n && v.every(Number.isFinite);
    const loop = path => Array.isArray(path) && path.length >= 3 && path.every(p => finite(p, 2));
    if (!carrier || ![lcd.origin, lcd.u, lcd.v, lcd.normal].every(v => finite(v, 3)) ||
        art?.kind !== 'presentation' || art.units !== 'mm' || !/^#[\da-f]{6}$/i.test(art.color) ||
        !art.polygons?.length || !art.polygons.every(p => loop(p.points) && (p.holes || []).every(loop))) return null;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const polygon of art.polygons) {
      for (const [x, y] of polygon.points) {
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
      }
    }
    const pad = 0.15;  // transparent margin against texture-edge sampling, millimetres
    const left = minX - pad;
    const top = maxY + pad;
    const width = maxX + pad - left;
    const height = top - minY + pad;
    const mask = document.createElement('canvas');
    mask.width = Math.max(32, Math.round(768 * width / Math.max(width, height)));
    mask.height = Math.max(32, Math.round(768 * height / Math.max(width, height)));
    const brush = mask.getContext('2d');
    brush.fillStyle = 'white';
    const sx = mask.width / width;
    const sy = mask.height / height;
    brush.setTransform(sx, 0, 0, -sy, -left * sx, top * sy);
    for (const polygon of art.polygons) {
      brush.beginPath();
      for (const ring of [polygon.points, ...(polygon.holes || [])]) {
        brush.moveTo(...ring[0]);
        for (let i = 1; i < ring.length; i++) brush.lineTo(...ring[i]);
        brush.closePath();
      }
      brush.fill('evenodd');
    }
    const texture = new T.CanvasTexture(mask);
    const origin = new T.Vector3(...lcd.origin);
    const u = new T.Vector3(...lcd.u).normalize();
    const v = new T.Vector3(...lcd.v).normalize();
    const normal = new T.Vector3(...lcd.normal).normalize();
    const ink = new T.Color(art.color);
    const materials = [];
    const restFrames = new WeakMap();
    for (const surface of carrier.surfaces) {
      const rest = surface.mesh.matrixWorld.clone();
      restFrames.set(surface.mesh, rest);
      function decorate(original) {
        const material = original.clone();
        material.onBeforeCompile = shader => {
          Object.assign(shader.uniforms, {
            atlasRest: { value: rest }, atlasOrigin: { value: origin }, atlasU: { value: u },
            atlasV: { value: v }, atlasNormal: { value: normal }, atlasInk: { value: ink },
            atlasMask: { value: texture }, atlasMin: { value: new T.Vector2(left, top - height) },
            atlasSize: { value: new T.Vector2(width, height) },
          });
          shader.vertexShader = shader.vertexShader.replace('#include <common>', `#include <common>
            uniform mat4 atlasRest;
            uniform vec3 atlasOrigin, atlasU, atlasV, atlasNormal;
            uniform vec2 atlasMin, atlasSize;
            varying vec3 vAtlasGlass;`)
            .replace('#include <begin_vertex>', `#include <begin_vertex>
            vec3 restDelta = (atlasRest * vec4(position, 1.0)).xyz - atlasOrigin;
            vec2 sheetMM = 1000.0 * vec2(dot(restDelta, atlasU), dot(restDelta, atlasV));
            vAtlasGlass = vec3((sheetMM - atlasMin) / atlasSize,
              dot(normalize(mat3(atlasRest) * normal), atlasNormal));`);
          shader.fragmentShader = shader.fragmentShader.replace('#include <common>', `#include <common>
            varying vec3 vAtlasGlass;
            uniform sampler2D atlasMask;
            uniform vec3 atlasInk;`)
            .replace('#include <opaque_fragment>', `
            if (vAtlasGlass.z > 0.96 && gl_FrontFacing) {
              vec2 uv = vAtlasGlass.xy;
              vec2 inside = step(vec2(0.0), uv) * step(uv, vec2(1.0));
              // Never extend a mipmapped edge texel across the surrounding dark glass.
              float graphic = texture2D(atlasMask, uv).a * inside.x * inside.y;
              // The catalog shows a powered black field; retain a little real glass
              // reflection and any selection emissive. With display off this code isn't used.
              outgoingLight = mix(totalEmissiveRadiance, outgoingLight, 0.14) + graphic * atlasInk;
            }
            #include <opaque_fragment>`);
        };
        material.customProgramCacheKey = () => 'atlas-lcd-surface-v1';
        materials.push(material);
        return material;
      }
      surface.lit = Array.isArray(surface.original) ? surface.original.map(decorate) : decorate(surface.original);
    }
    return {
      carrier,
      windowId: lcd.windowId,
      isLitHit(hit, ray) {
        if (!carrier.screenOn || !hit?.face) return false;
        const rest = restFrames.get(hit.object);
        if (!rest) return false;
        const facing = hit.face.normal.clone();
        if (facing.transformDirection(hit.object.matrixWorld).dot(ray.direction) >= 0) return false;
        if (facing.copy(hit.face.normal).transformDirection(rest).dot(normal) <= 0.96) return false;
        // Sample the same drawn mask as the shader, in its original carrier frame.
        const p = hit.object.worldToLocal(hit.point.clone()).applyMatrix4(rest).sub(origin);
        const x = Math.floor((1000 * p.dot(u) - left) * sx);
        const y = Math.floor((top - 1000 * p.dot(v)) * sy);
        if (x < 0 || y < 0 || x >= mask.width || y >= mask.height) return false;
        return brush.getImageData(x, y, 1, 1).data[3] >= 128;
      },
      dispose() {
        texture.dispose();
        for (const material of materials) material.dispose();
      },
    };
  }

  // Clone only selected/recoloured materials. Adjacent parts often share a glTF material.
  function stylePart(part, finish, selected, ink) {
    const { variants, surfaces } = part;
    const base = s => part.screenOn && s.lit ? s.lit : s.original;
    if (!finish && !selected) {
      for (const surface of surfaces) surface.mesh.material = base(surface);
      for (const material of variants.values()) material.dispose();
      variants.clear();
      return;
    }
    function variant(original) {
      if (!variants.has(original)) {
        const local = original.clone();
        local.onBeforeCompile = original.onBeforeCompile;
        local.customProgramCacheKey = original.customProgramCacheKey;
        variants.set(original, local);
      }
      const material = variants.get(original);
      if (material.color) {
        material.color.copy(original.color);
        if (finish) material.color.set(finish);
      }
      if (material.emissive) {
        material.emissive.copy(original.emissive);
        material.emissiveIntensity = original.emissiveIntensity;
        if (selected) {
          material.emissive.add(ink);
          material.emissiveIntensity = Math.max(1, material.emissiveIntensity);
        }
      } else if (selected && material.color) {
        material.color.lerp(ink, 0.4);
      }
      return material;
    }
    for (const surface of surfaces) {
      const original = base(surface);
      surface.mesh.material = Array.isArray(original) ? original.map(variant) : variant(original);
    }
  }

  function disposeModel(root) {
    const resources = new Set();
    const textures = new Set();
    root.traverse(object => {
      if (!object.isMesh) return;
      resources.add(object.geometry);
      for (const material of [].concat(object.material)) {
        resources.add(material);
        for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
      }
    });
    for (const resource of resources) resource.dispose();
    for (const texture of textures) {
      texture.dispose();
      texture.image?.close?.();
    }
  }

  function makeBackdrop(T) {
    const strip = document.createElement('canvas');
    strip.width = 2;
    strip.height = 128;
    const paint = strip.getContext('2d');
    const wash = paint.createLinearGradient(0, 0, 0, strip.height);
    wash.addColorStop(0, '#e5e3dd');
    wash.addColorStop(0.56, '#f2f0e9');
    wash.addColorStop(1, '#e5e2da');
    paint.fillStyle = wash;
    paint.fillRect(0, 0, strip.width, strip.height);
    const texture = new T.CanvasTexture(strip);
    texture.colorSpace = T.SRGBColorSpace;
    return texture;
  }

  // A local linear-radiance light field. Broad neutral reflectors reveal satin edges and
  // conductive pads without replacing calibrated base colours or guessing material types.
  function makeEnvironment(T) {
    const width = 256;
    const height = 128;
    const pixels = new Float32Array(width * height * 4);
    const panels = [
      { direction: new T.Vector3(-0.8, 0.9, 0.7).normalize(), power: 12, gain: 5.0 },
      { direction: new T.Vector3(0.9, 0.35, -0.8).normalize(), power: 19, gain: 4.2 },
      { direction: new T.Vector3(-0.1, 0.55, -1).normalize(), power: 8, gain: 1.4 },
    ];
    const ray = new T.Vector3();
    for (let y = 0; y < height; y++) {
      const latitude = Math.PI * ((y + 0.5) / height - 0.5);
      for (let x = 0; x < width; x++) {
        const longitude = 2 * Math.PI * ((x + 0.5) / width - 0.5);
        ray.set(
          Math.cos(longitude) * Math.cos(latitude),
          Math.sin(latitude),
          Math.sin(longitude) * Math.cos(latitude),
        );
        let light = 0.18 + 0.20 * (ray.y + 1);
        for (const panel of panels) light += panel.gain * Math.pow(Math.max(0, ray.dot(panel.direction)), panel.power);
        const i = (y * width + x) * 4;
        pixels[i] = pixels[i + 1] = pixels[i + 2] = light;
        pixels[i + 3] = 1;
      }
    }
    const texture = new T.DataTexture(pixels, width, height, T.RGBAFormat, T.FloatType);
    texture.mapping = T.EquirectangularReflectionMapping;
    texture.colorSpace = T.LinearSRGBColorSpace;
    texture.needsUpdate = true;
    return texture;
  }

  function makeStudio(T, renderer, scene) {
    scene.background = makeBackdrop(T);
    scene.environment = makeEnvironment(T);
    scene.environmentIntensity = 1.14;
    const sky = new T.HemisphereLight(0xfff9ed, 0xc7c6c1, 0.66);
    const key = new T.DirectionalLight(0xfff7eb, 1.9);
    const rim = new T.DirectionalLight(0xe5efff, 1.5);
    rim.position.set(0.7, 0.8, -1);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.radius = 9;
    key.shadow.bias = -0.0002;
    const floor = new T.Mesh(
      new T.PlaneGeometry(1, 1),
      new T.ShadowMaterial({ color: 0x524d47, depthWrite: false }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(sky, key, key.target, rim, floor);
    // Shadows only change with model visibility or placement, not orbit/pan/zoom.
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = T.PCFShadowMap;
    renderer.shadowMap.autoUpdate = false;
    const keyDirection = new T.Vector3(-0.43, 2.4, 0.54).normalize();
    return {
      // The pinned bundle already supplies a real OrthographicCamera via DirectionalLight.
      // This detached camera has independent transforms/frustum; never aim the light itself.
      orthographic: key.shadow.camera.clone(),
      place(bounds, center, radius, contact) {
        // A grounded assembly/part has a contact shadow, a fully exploded diagram has none.
        floor.visible = contact > 0 && !bounds.isEmpty();
        floor.material.opacity = 0.105 * contact;
        if (bounds.isEmpty()) return;
        floor.scale.setScalar(8 * radius);
        floor.position.set(center.x, bounds.min.y - radius * 0.002, center.z);
        key.target.position.copy(center);
        key.position.copy(center).addScaledVector(keyDirection, 4 * radius);
        const half = radius * 2;
        Object.assign(key.shadow.camera, {
          left: -half, right: half, bottom: -half, top: half,
          near: radius * 0.1, far: radius * 8,
        });
        key.shadow.camera.updateProjectionMatrix();
        renderer.shadowMap.needsUpdate = floor.visible;
      },
      dispose() {
        floor.geometry.dispose();
        floor.material.dispose();
        key.shadow.dispose();
        scene.background.dispose();
        scene.environment.dispose();
        scene.background = null;
        scene.environment = null;
      },
    };
  }

  // Solve the perspective frustum inequalities in the eye's own basis for the corners
  // of each visible mesh-node box, including its explosion offset. No nominal product size.
  function fitMeasure(T, boxes, center, eye, camera, aspect) {
    const right = new T.Vector3().crossVectors(camera.up, eye).normalize();
    const up = new T.Vector3().crossVectors(eye, right);
    const parallel = camera.isOrthographicCamera;
    const spanY = parallel ? 0.5 * 0.84 : Math.tan(camera.fov * Math.PI / 360) * 0.84;
    const spanX = spanY * aspect;
    const corner = new T.Vector3();
    let distance = 0.000002;
    for (const { min, max } of boxes) {
      for (let i = 0; i < 8; i++) {
        corner.set(i & 1 ? max.x : min.x, i & 2 ? max.y : min.y, i & 4 ? max.z : min.z).sub(center);
        const depth = parallel ? 0 : corner.dot(eye);
        distance = Math.max(
          distance,
          depth + Math.abs(corner.dot(right)) / spanX,
          depth + Math.abs(corner.dot(up)) / spanY,
        );
      }
    }
    return distance;
  }

  function bindPicking(T, canvas, activeCamera, model, visibleMeshes, screen, onHit) {
    const ray = new T.Raycaster();
    const cursor = new T.Vector2();
    let press = null;
    function down(event) {
      if (press || !event.isPrimary || event.button !== 0 || event.shiftKey || event.ctrlKey || event.metaKey) {
        press = null;
        return;
      }
      press = { id: event.pointerId, x: event.clientX, y: event.clientY };
    }
    function move(event) {
      if (press?.id === event.pointerId && Math.hypot(event.clientX - press.x, event.clientY - press.y) > 5) press = null;
    }
    function cancel() {
      press = null;
    }
    function up(event) {
      if (press?.id !== event.pointerId) return;
      move(event);
      if (!press) return;
      press = null;
      const rect = canvas.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      cursor.set(2 * (event.clientX - rect.left) / rect.width - 1, 1 - 2 * (event.clientY - rect.top) / rect.height);
      const camera = activeCamera();
      camera.updateMatrixWorld();
      ray.setFromCamera(cursor, camera);
      const hits = ray.intersectObjects(visibleMeshes(), false);
      if (!hits.length) return;
      let id = model.owner.get(hits[0].object);
      // Only a lit stroke seen through the registered cover targets the underlying LCD.
      // The off state, dark surround and a removed window all pick the nearest part.
      if (screen && id === screen.windowId) {
        const behind = hits.find(hit => model.owner.get(hit.object) !== id);
        if (screen.isLitHit(behind, ray.ray)) id = screen.carrier.id;
      }
      onHit(id);
    }
    const events = { pointerdown: down, pointermove: move, pointerup: up, pointercancel: cancel, lostpointercapture: cancel };
    for (const [type, listener] of Object.entries(events)) canvas.addEventListener(type, listener);
    return () => {
      for (const [type, listener] of Object.entries(events)) canvas.removeEventListener(type, listener);
    };
  }

  /**
   * Decode the embedded GLB and resolve after the first frame (when canvas is visible).
   * Only a pointer hit calls onPick. The host owns the DOM, catalog and error presentation.
   * Initialization errors report once via onError and reject the same message.
   */
  async function create(canvas, data, callbacks = {}) {
    const T = window.AtlasThree;
    let disposed = false;
    let lost = false;
    let frame = 0;
    const cleanup = [];
    function destroy() {
      if (disposed) return;
      disposed = true;
      cancelAnimationFrame(frame);
      while (cleanup.length) cleanup.pop()();
    }
    try {
      if (!T) throw new Error('Не найдена локальная библиотека three-atlas.js.');
      if (!canvas?.getContext || !Array.isArray(data?.parts) || !Array.isArray(data?.groups)) {
        throw new Error('Не переданы canvas или каталог сцены.');
      }
      let renderer;
      try {
        renderer = new T.WebGLRenderer({ canvas, alpha: false, antialias: true });
      } catch {
        throw new Error('Браузер не создал контекст WebGL 2. Каталог и данные деталей доступны без 3D.');
      }
      cleanup.push(() => renderer.dispose());
      renderer.outputColorSpace = T.SRGBColorSpace;
      renderer.toneMapping = T.NeutralToneMapping;
      renderer.toneMappingExposure = 1.22;

      const gltf = await parseEmbeddedGLB(T, data.glbBase64);
      const root = gltf.scene;
      cleanup.push(() => {
        disposeModel(root);
        root.clear();
      });
      const model = indexModel(T, gltf, data);
      const screen = makeScreen(T, model, data.presentation?.lcd);
      const scene = new T.Scene();
      scene.add(root);
      cleanup.push(() => {
        scene.clear();
        model.parts.clear();
        model.groups.clear();
      });
      const studio = makeStudio(T, renderer, scene);
      cleanup.push(() => studio.dispose());
      const perspective = new T.PerspectiveCamera(31, 1, 0.001, 2);
      const orthographic = studio.orthographic;
      let camera;
      let controls;
      let parallelHeight = 0.18;
      const { cursor, touchAction } = canvas.style;

      const bounds = new T.Box3();
      const center = new T.Vector3();
      const ink = new T.Color(0x399eae).multiplyScalar(0.64);
      let radius = 0;
      let visible = [];
      let pickable = [];
      let group = null;
      let isolated = null;
      let selected = null;
      let explode = 0;
      let finishes = new Map();
      let offsets = new Map();
      let framing = false;
      let fitScope = 'visible';
      let width = 0;
      let height = 0;
      let pixelRatio = 0;

      function draw() {
        frame = 0;
        if (disposed || lost || !width || !height) return;
        const orbit = camera.position.distanceTo(controls.target);
        camera.near = Math.max(1e-8, Math.min(orbit * 0.025, radius * 0.06));
        camera.far = Math.max(camera.near * 100, camera.position.distanceTo(center) + radius * 6);
        camera.updateProjectionMatrix();
        renderer.render(scene, camera);
      }
      function invalidate() {
        if (!frame && !disposed && !lost) frame = requestAnimationFrame(draw);
      }
      function change() {
        if (!framing) fitScope = null;
        invalidate();
      }
      function releaseControls() {
        if (!controls) return;
        controls.removeEventListener('change', change);
        controls.dispose();
      }
      function updateProjection() {
        const aspect = width && height ? width / height : 1;
        perspective.aspect = aspect;
        perspective.updateProjectionMatrix();
        orthographic.top = parallelHeight / 2;
        orthographic.bottom = -orthographic.top;
        orthographic.right = orthographic.top * aspect;
        orthographic.left = -orthographic.right;
        orthographic.updateProjectionMatrix();
      }
      function useCamera(next, up = upright) {
        if (camera === next && camera.up.x === up[0] && camera.up.y === up[1] && camera.up.z === up[2]) return;
        // OrbitControls caches its camera-up basis at construction. Recreate on basis
        // change so top/bottom are exactly axial (no epsilon tilt) and orbit still works.
        releaseControls();
        camera = next;
        camera.up.fromArray(up);
        controls = new T.OrbitControls(camera, canvas);
        controls.rotateSpeed = 0.78;
        controls.zoomToCursor = true;
        controls.enableDamping = false;
        controls.autoRotate = false;
        controls.minDistance = Math.max(1e-8, radius * 0.00008);
        controls.minZoom = 0.01;
        controls.maxZoom = 8000;
        controls.addEventListener('change', change);
      }
      useCamera(perspective);
      cleanup.push(() => {
        releaseControls();
        Object.assign(canvas.style, { cursor, touchAction });
      });

      function layout() {
        bounds.makeEmpty();
        visible = [];
        pickable = [];
        for (const g of model.groups.values()) g.node.position.copy(g.rest).addScaledVector(g.delta, explode);
        for (const part of model.parts.values()) {
          // Exported group frames are identity. Offsets are absolute, additive world metres,
          // independent of visibility; changing view or isolating never moves a physical part.
          const offset = offsets.get(part.id);
          // A part override replaces its group's full-explosion vector, not adds to it.
          part.node.position.copy(part.origin).addScaledVector(part.relative, explode);
          if (offset) part.node.position.add(offset);
          part.node.visible = isolated ? part.id === isolated : !group || part.group.id === group;
          if (!part.node.visible) continue;
          part.box.copy(part.rest);
          part.box.min.addScaledVector(part.delta, explode);
          part.box.max.addScaledVector(part.delta, explode);
          if (offset) part.box.translate(offset);
          bounds.union(part.box);
          visible.push(part);
          for (const { mesh } of part.surfaces) pickable.push(mesh);
        }
        root.updateMatrixWorld(true);
        bounds.getCenter(center);
        radius = Math.max(0.000001, bounds.getSize(new T.Vector3()).length() / 2);
        controls.minDistance = Math.max(1e-8, radius * 0.00008);
        const contact = group || isolated ? 1 : offsets.size ? 0 : Math.max(0, 1 - 2 * explode);
        studio.place(bounds, center, radius, contact);
      }
      function aim(direction, scope = 'visible') {
        if (disposed || !visible.length) return;
        const detail = scope === 'part' && model.parts.get(selected);
        const boxes = detail && detail.node.visible ? [detail.box] : visible.map(part => part.box);
        const pivot = boxes.length === 1 ? boxes[0].getCenter(new T.Vector3()) : center;
        const eye = direction ? new T.Vector3(...direction) : camera.position.clone().sub(controls.target);
        if (!eye.lengthSq()) eye.fromArray(assemblyEye);
        eye.normalize();
        const aspect = width && height ? width / height : 1;
        const fit = fitMeasure(T, boxes, pivot, eye, camera, aspect);
        let distance = fit;
        if (camera === orthographic) {
          parallelHeight = fit;
          if (!group && !isolated && boxes.length > 1) {
            // Common square metric frame across all six assembled projections. On a non-
            // square canvas add field at the sides, not a different product magnification.
            const size = bounds.getSize(new T.Vector3());
            const side = Math.max(size.x, size.y, size.z) / 0.84;
            parallelHeight = Math.max(fit, side / Math.min(1, aspect));
          }
          camera.zoom = 1;
          distance = radius * 4;
          updateProjection();
        }
        controls.maxDistance = Math.max(radius * 32, distance * 10);
        framing = true;
        controls.target.copy(pivot);
        camera.position.copy(pivot).addScaledVector(eye, distance);
        controls.update();
        framing = false;
        fitScope = scope;
        invalidate();
      }
      function bestEye() {
        return model.parts.get(isolated)?.eye || groupEye[group] || assemblyEye;
      }
      function resize() {
        const rect = canvas.getBoundingClientRect();
        const w = Math.round(rect.width);
        const h = Math.round(rect.height);
        const dpr = Math.min(window.devicePixelRatio || 1, 2, Math.sqrt(4000000 / Math.max(1, w * h)));
        if (w === width && h === height && dpr === pixelRatio) return;
        width = w;
        height = h;
        pixelRatio = dpr;
        if (!width || !height) return;
        renderer.setDrawingBufferSize(width, height, pixelRatio);
        updateProjection();
        if (fitScope) aim(null, fitScope);
        invalidate();
      }
      const resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(canvas);
      window.addEventListener('resize', resize);
      cleanup.push(() => {
        resizeObserver.disconnect();
        window.removeEventListener('resize', resize);
      });

      function paint(id) {
        const part = model.parts.get(id);
        if (part) stylePart(part, finishes.get(id), id === selected, ink);
      }
      function select(id) {
        if (disposed || id === selected || (id != null && !model.parts.has(id))) return;
        const previous = selected;
        selected = id ?? null;
        paint(previous);
        paint(selected);
        invalidate();
      }
      function setScreenOn(on) {
        if (disposed || !screen) return false;
        screen.carrier.screenOn = Boolean(on);
        paint(screen.carrier.id);
        invalidate();
        return true;
      }
      cleanup.push(() => {
        if (screen) {
          screen.carrier.screenOn = false;
          stylePart(screen.carrier, null, false, ink);
          screen.dispose();
        }
        for (const part of model.parts.values()) if (part.variants.size) stylePart(part, null, false, ink);
        visible = [];
        pickable = [];
        finishes.clear();
        offsets.clear();
      });
      cleanup.push(bindPicking(T, canvas, () => camera, model, () => pickable, screen, id => {
        select(id);
        callbacks.onPick?.(id);
      }));
      function contextLost(event) {
        event.preventDefault();
        lost = true;
        callbacks.onError?.('Потерян контекст WebGL. Каталог деталей остаётся доступен.');
      }
      function contextRestored() {
        lost = false;
        renderer.shadowMap.needsUpdate = true;
        invalidate();
      }
      canvas.addEventListener('webglcontextlost', contextLost);
      canvas.addEventListener('webglcontextrestored', contextRestored);
      cleanup.push(() => {
        canvas.removeEventListener('webglcontextlost', contextLost);
        canvas.removeEventListener('webglcontextrestored', contextRestored);
      });

      layout();
      resize();
      aim(bestEye());
      if (screen) setScreenOn(true);
      if (renderer.getContext().isContextLost()) throw new Error('Потерян контекст WebGL.');
      cancelAnimationFrame(frame);
      draw();
      return Object.freeze({
        setGroup(id) {
          if (disposed) return;
          const next = id === 'all' || id === 'All' || id == null ? null : id;
          if (next && !model.groups.has(next)) return;
          group = next;
          isolated = null;
          layout();
          useCamera(perspective);
          aim(bestEye());
        },
        setExplode(value) {
          if (disposed || !Number.isFinite(value)) return;
          const next = Math.max(0, Math.min(1, value));
          if (next === explode) return;
          explode = next;
          layout();
          aim(null, fitScope || 'visible');
        },
        setOffsets(map) {
          if (disposed) return;
          const next = new Map();
          for (const [id, xyz] of map instanceof Map ? map : Object.entries(map || {})) {
            if (!model.parts.has(id) || !Array.isArray(xyz) || xyz.length !== 3 || !xyz.every(Number.isFinite)) continue;
            if (xyz.some(value => value !== 0)) next.set(id, new T.Vector3(...xyz));
          }
          if (next.size === offsets.size && [...next].every(([id, v]) => offsets.get(id)?.equals(v))) return;
          offsets = next;
          layout();
          aim(null, fitScope || 'visible');
        },
        setScreenOn,
        select,
        isolate(id) {
          if (disposed || (id != null && !model.parts.has(id))) return;
          isolated = id ?? null;
          layout();
          useCamera(perspective);
          aim(bestEye());
        },
        fit() {
          aim(null);
        },
        setView(name) {
          if (disposed) return;
          const detail = model.parts.get(selected);
          if (name === 'iso' || name === 'part') {
            useCamera(perspective);
            if (name === 'part') aim(detail?.node.visible ? detail.eye : bestEye(), 'part');
            else aim(bestEye());
          } else if (Object.hasOwn(fixedViews, name)) {
            const view = fixedViews[name];
            useCamera(orthographic, view.up);
            aim(view.eye);
          }
        },
        setFinish(map) {
          if (disposed) return;
          const entries = map instanceof Map ? map : Object.entries(map || {});
          const next = new Map();
          for (const [id, hex] of entries) {
            if (model.parts.has(id) && typeof hex === 'string' && /^#(?:[\da-f]{3}|[\da-f]{6})$/i.test(hex)) {
              next.set(id, hex);
            }
          }
          const old = finishes;
          finishes = next;
          for (const id of new Set([...old.keys(), ...next.keys()])) if (old.get(id) !== next.get(id)) paint(id);
          invalidate();
        },
        destroy,
      });
    } catch (error) {
      destroy();
      const message = `Не удалось открыть 3D: ${error.message || error}`;
      callbacks.onError?.(message);
      throw new Error(message);
    }
  }

  window.AtlasViewport = Object.freeze({ create });
})();
