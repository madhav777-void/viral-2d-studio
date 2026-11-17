// Real 3D models (GLB / glTF) for the things primitives can't sell: sharks, organs, animals, vehicles, landmarks.
// A model loads ONCE at boot and is cloned per use, so render speed is the same as for hand-built meshes
// (keep each model under ~100k triangles; shrink bigger ones with: npx @gltf-transform/cli optimize in.glb out.glb).
//
//   import { preload, model, pose, clips } from './core/models.js';
//   await preload(['shark', 'liver']);                       // in buildShots (make it async) or at the top of shots.js
//   const shark = model('shark', { size: 4 });               // longest side 4 m, centred, sitting on y = 0
//   const liver = model('liver', { size: 0.22, fit: 'height', ground: false, color: '#B5473C' });
//   pose(shark, 'Swim', t);                                  // animated GLB: set the clip to time t (pure function of t)
//
// Files: <project>/assets/models/<name>.glb (Claude copies them in from ~/.omni-shorts/models/ or wherever it found
// them). Credit every model you did not make in <project>/assets/models/CREDITS.txt (name, author, licence, URL).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { clone as skClone } from 'three/addons/utils/SkeletonUtils.js';

const loader = new GLTFLoader(), cache = new Map();

/** load models by name from assets/models/<name>.glb (or .gltf); throws a clear error if one is missing */
export async function preload(names) {
  await Promise.all(names.filter((n) => !cache.has(n)).map(async (n) => {
    let gl = null, err = null;
    for (const ext of ['glb', 'gltf']) {
      try { gl = await loader.loadAsync(`assets/models/${n}.${ext}`); break; } catch (e) { err = e; }
    }
    if (!gl) throw new Error(`model "${n}" not found in assets/models/ (${err?.message || err})`);
    cache.set(n, gl);
  }));
}

/** names of the animation clips inside a model */
export const clips = (name) => (cache.get(name)?.animations || []).map((a) => a.name);

/**
 * a fresh copy of a loaded model, normalised:
 *   size   target size in metres · fit 'max' (longest side) | 'height' | 'length' (x) | 'none' (keep the file's scale)
 *   ground true: bottom at y = 0 (else centred on 0) · centre x/z on 0
 *   color  tint every material (keeps its texture) · shadow: cast + receive · rough: override roughness
 */
export function model(name, { size = 1, fit = 'max', ground = true, color = null, shadow = true, rough = null } = {}) {
  const gl = cache.get(name);
  if (!gl) throw new Error(`model "${name}" was not preloaded: await preload(['${name}']) first`);
  const src = gl.scene, obj = gl.animations?.length ? skClone(src) : src.clone(true);
  obj.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = o.receiveShadow = shadow;
    o.material = Array.isArray(o.material) ? o.material.map((m) => m.clone()) : o.material.clone();
    for (const m of [].concat(o.material)) {
      if (color && m.color) m.color.multiply(new THREE.Color(color));
      if (rough != null && 'roughness' in m) m.roughness = rough;
    }
  });
  const inner = new THREE.Group(); inner.add(obj);
  const box = new THREE.Box3().setFromObject(obj), sz = box.getSize(new THREE.Vector3()), c = box.getCenter(new THREE.Vector3());
  const ref = fit === 'height' ? sz.y : fit === 'length' ? sz.x : fit === 'none' ? 0 : Math.max(sz.x, sz.y, sz.z);
  const k = ref > 0 ? size / ref : 1;
  obj.position.set(-c.x, ground ? -box.min.y : -c.y, -c.z);
  inner.scale.setScalar(k);
  const g = new THREE.Group(); g.add(inner);
  g.userData.model = { name, gl, root: obj };
  return g;
}

/** play animation clip `clip` (name or index) of a model() copy at time t, looping. Pure function of t. */
export function pose(g, clip = 0, t = 0, { speed = 1, loop = true } = {}) {
  const u = g.userData.model; if (!u?.gl.animations?.length) return;
  const a = typeof clip === 'number' ? u.gl.animations[clip] : u.gl.animations.find((x) => x.name === clip) || u.gl.animations[0];
  if (!u.mixer) { u.mixer = new THREE.AnimationMixer(u.root); u.actions = new Map(); }
  let act = u.actions.get(a.name);
  if (!act) { act = u.mixer.clipAction(a); act.play(); u.actions.set(a.name, act); }
  for (const [n, other] of u.actions) other.weight = n === a.name ? 1 : 0;
  const tt = t * speed; act.time = loop ? ((tt % a.duration) + a.duration) % a.duration : Math.min(tt, a.duration);
  u.mixer.update(0);
}
