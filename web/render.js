/* Photoreal render pipeline for the walkthrough.
 *
 *   physical sky + sun  ->  image-based lighting (PMREM)  ->  soft shadow-mapped sun
 *   scene (HDR half-float)  ->  ambient occlusion  ->  bloom  ->  ACES filmic tone map + sRGB  ->  FXAA
 *
 * Three quality levels: photo (everything), balanced (no AO / bloom, smaller shadow map), fast (plain forward render).
 * Works with three.js r128 (global build) plus the example passes bundled in vendor/three-extras.js.
 */
(function () {
  'use strict';

  const QUAL = {
    photo:    { composer: true,  sao: true,  bloom: true,  shadow: 4096, pr: 1.5 },
    balanced: { composer: true,  sao: false, bloom: false, shadow: 2048, pr: 1.25 },
    fast:     { composer: false, sao: false, bloom: false, shadow: 0,    pr: 1.0 },
  };

  const FinalShader = {
    uniforms: { tDiffuse: { value: null }, exposure: { value: 1 }, time: { value: 0 }, vignette: { value: 0.16 }, grain: { value: 0.010 } },
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: [
      'uniform sampler2D tDiffuse; uniform float exposure; uniform float time; uniform float vignette; uniform float grain; varying vec2 vUv;',
      'vec3 aces(vec3 x){ const float a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14; return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0); }',
      'vec3 toSRGB(vec3 c){ return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c)); }',
      'float hash(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }',
      'void main(){',
      '  vec3 c = texture2D(tDiffuse, vUv).rgb * exposure;',
      '  c = aces(c);',
      '  vec2 q = vUv - 0.5; c *= 1.0 - vignette * dot(q, q) * 2.2;',
      '  c = toSRGB(c);',
      '  c += (hash(vUv * vec2(1931.0, 1087.0) + time) - 0.5) * grain;',
      '  gl_FragColor = vec4(c, 1.0);',
      '}',
    ].join('\n'),
  };

  function create(ctx) {
    const { THREE, renderer, scene, camera, center } = ctx;
    const S = { quality: ctx.quality || 'photo', tod: 0.64, ao: true, exposure: 1, env: 1, auto: !ctx.forced, mode: 'composer' };
    const pmrem = new THREE.PMREMGenerator(renderer);
    const materials = [];
    let composer = null, passes = {}, envRT = null, W = 1, H = 1, dprMax = Math.min(window.devicePixelRatio || 1, 2);
    let frames = 0, acc = 0, onAuto = null, needShadow = true;

    // ---------------------------------------------------------------- lights
    const hemi = new THREE.HemisphereLight(0xf2ecdf, 0x8a7a64, 0.3);
    scene.add(hemi);
    const sun = new THREE.DirectionalLight(0xfff0dc, 2.2);
    sun.castShadow = true;
    sun.target.position.set(center.x, 1.5, center.z);
    scene.add(sun); scene.add(sun.target);
    const sc = sun.shadow.camera;
    sc.left = -17; sc.right = 17; sc.top = 17; sc.bottom = -17; sc.near = 1; sc.far = 140;
    sun.shadow.bias = -0.0003; sun.shadow.normalBias = 0.03; sun.shadow.radius = 3;
    const bounce = [0, 1, 2].map(() => { const l = new THREE.PointLight(0xfff3e4, 0, 9, 2); l.position.set(0, -50, 0); scene.add(l); return l; });

    // ---------------------------------------------------------------- sky + image-based lighting
    const sky = new THREE.Sky();
    sky.scale.setScalar(50);
    const u = sky.material.uniforms;
    u.turbidity.value = 6; u.rayleigh.value = 0.85; u.mieCoefficient.value = 0.007; u.mieDirectionalG.value = 0.86;
    const envScene = new THREE.Scene(); envScene.add(sky);

    function setTime(t, quiet) {
      S.tod = t;
      const el = 11 + 40 * Math.sin(Math.PI * t), az = (-140 + 280 * t) * Math.PI / 180, e = el * Math.PI / 180;   // az 0 = street side
      const dir = new THREE.Vector3(Math.sin(az) * Math.cos(e), Math.sin(e), Math.cos(az) * Math.cos(e));
      sun.position.set(center.x + dir.x * 70, dir.y * 70 + 1.5, center.z + dir.z * 70);
      u.sunPosition.value.copy(dir);
      const k = Math.min(1, Math.max(0, (el - 11) / 36));                        // low sun = warm and weaker
      sun.color.setRGB(1, 0.72 + 0.25 * k, 0.5 + 0.42 * k);
      sun.intensity = 0.9 + 1.5 * Math.sin(e);
      if (envRT) envRT.dispose();
      envRT = pmrem.fromScene(envScene);
      scene.environment = envRT.texture; scene.background = envRT.texture;
      needShadow = true;
      return { elevation: el };
    }

    // ---------------------------------------------------------------- composer
    function supportsHDR() {
      const gl = renderer.getContext();
      return renderer.capabilities.isWebGL2 && (renderer.extensions.has('EXT_color_buffer_float') || renderer.extensions.has('EXT_color_buffer_half_float') || !!gl.getExtension('EXT_color_buffer_float'));
    }
    function buildComposer() {
      const rt = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType, format: THREE.RGBAFormat, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter });
      composer = new THREE.EffectComposer(renderer, rt);
      composer.setSize(W, H);
      passes.render = new THREE.RenderPass(scene, camera);
      passes.sao = new THREE.SAOPass(scene, camera, false, true, new THREE.Vector2(W, H));
      Object.assign(passes.sao.params, { saoBias: 0.15, saoIntensity: 0.55, saoScale: camera.far, saoKernelRadius: 70, saoMinResolution: 0, saoBlur: true, saoBlurRadius: 10, saoBlurStdDev: 5, saoBlurDepthCutoff: 0.003 });
      const sr = passes.sao.render.bind(passes.sao);      // glass, labels and the like live on layer 1 and must not occlude
      passes.sao.render = function () { camera.layers.disable(1); sr.apply(null, arguments); camera.layers.enable(1); };
      passes.bloom = new THREE.UnrealBloomPass(new THREE.Vector2(W, H), 0.16, 0.55, 1.25);
      passes.final = new THREE.ShaderPass(FinalShader);
      passes.fxaa = new THREE.ShaderPass(THREE.FXAAShader);
      ['render', 'sao', 'bloom', 'final', 'fxaa'].forEach((k) => composer.addPass(passes[k]));
      passes.fxaa.material.uniforms.resolution.value.set(1 / W, 1 / H);
    }

    function applyQuality() {
      const q = QUAL[S.quality];
      let useComposer = q.composer;
      if (useComposer && !supportsHDR()) { useComposer = false; S.quality = 'fast'; }
      S.mode = useComposer ? 'composer' : 'direct';
      renderer.setPixelRatio(Math.min(dprMax, QUAL[S.quality].pr));
      renderer.shadowMap.enabled = QUAL[S.quality].shadow > 0;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      renderer.shadowMap.autoUpdate = false;
      sun.castShadow = renderer.shadowMap.enabled;
      const n = QUAL[S.quality].shadow || 1024;
      if (sun.shadow.mapSize.x !== n) { sun.shadow.mapSize.set(n, n); if (sun.shadow.map) { sun.shadow.map.dispose(); sun.shadow.map = null; } }
      renderer.outputEncoding = THREE.sRGBEncoding;
      renderer.toneMapping = useComposer ? THREE.NoToneMapping : THREE.ACESFilmicToneMapping;
      if (useComposer && !composer) buildComposer();
      if (composer) { passes.sao.enabled = q.sao && S.ao; passes.bloom.enabled = q.bloom; }
      const size = renderer.getSize(new THREE.Vector2());
      resize(size.x, size.y);
      scene.traverse((o) => { if (o.material) [].concat(o.material).forEach((m) => { m.needsUpdate = true; }); });
      needShadow = true;
    }

    function resize(w, h) {
      renderer.setSize(w, h, false);
      const pr = renderer.getPixelRatio();
      W = Math.max(2, Math.round(w * pr)); H = Math.max(2, Math.round(h * pr));
      if (composer) {
        composer.setSize(W, H);
        passes.fxaa.material.uniforms.resolution.value.set(1 / W, 1 / H);
      }
    }

    // ---------------------------------------------------------------- per-frame
    function render(dt) {
      if (needShadow) { renderer.shadowMap.needsUpdate = true; needShadow = false; }
      if (S.auto && dt > 0) {
        acc += dt; frames++;
        if (frames >= 90) {
          const avg = acc / frames; frames = 0; acc = 0;
          const next = S.quality === 'photo' && avg > 0.06 ? 'balanced' : (S.quality === 'balanced' && avg > 0.075 ? 'fast' : null);
          if (next) { setQuality(next, true); if (onAuto) onAuto(next); }
        }
      }
      if (S.mode === 'composer') {
        passes.final.uniforms.exposure.value = S.exposure;
        passes.final.uniforms.time.value = (performance.now() % 1000) / 1000;
        composer.render(dt);
      } else {
        renderer.toneMappingExposure = S.exposure;
        renderer.render(scene, camera);
      }
    }

    function setQuality(q, auto) {
      if (!QUAL[q]) return;
      S.quality = q; if (!auto) S.auto = false;
      applyQuality();
    }

    /** eye adaptation: brighter exposure and weaker sky light when you are indoors */
    function adapt(inside, dt) {
      const k = Math.min(1, dt * 2.2);
      S.exposure += ((0.36 + 0.58 * inside) - S.exposure) * k;
      const env = 1.0 - 0.8 * inside;
      if (Math.abs(env - S.env) > 0.01) {
        S.env = env;
        materials.forEach((m) => { m.envMapIntensity = (m.userData.env0 === undefined ? 1 : m.userData.env0) * env; });
      }
      hemi.intensity = 0.3 - 0.03 * inside;          // warm neutral fill stays on indoors
    }

    function registerMaterials(list) {
      list.forEach((m) => { if (m && materials.indexOf(m) < 0) { materials.push(m); if (m.envMapIntensity !== undefined) m.envMapIntensity = (m.userData.env0 === undefined ? 1 : m.userData.env0) * S.env; } });
    }

    // initial build
    setTime(S.tod);
    applyQuality();
    const api = {
      state: S, sun, hemi, bounce, QUAL,
      setTime, setQuality, resize, render, adapt, registerMaterials,
      invalidateShadows() { needShadow = true; },
      setAO(on) { S.ao = on; if (composer) passes.sao.enabled = QUAL[S.quality].sao && on; },
      onAutoQuality(fn) { onAuto = fn; },
    };
    return api;
  }

  window.RenderFX = { create };
})();
