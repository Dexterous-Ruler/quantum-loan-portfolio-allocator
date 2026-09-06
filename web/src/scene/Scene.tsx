/** The bank floor. People stand in an arc; funded ones step forward onto the lit approval stage.
 *  Beams between funded people are the live ZZ couplings of the Hamiltonian (same-segment when
 *  diversification is on, opposite-group when fairness is on). The vault gauge shows capital used. */
import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, ContactShadows, Grid, Line } from "@react-three/drei";
import * as THREE from "three";
import gsap from "gsap";
import type { Problem, Bits } from "../lib/problem";
import { used } from "../lib/problem";
import { Person } from "./Person";

export interface SceneProps {
  P: Problem; x: Bits; manual: Bits | null; gOn: boolean; lOn: boolean; solveTick: number;
  onPick: (i: number) => void; reduced: boolean;
}

function layout(n: number): [number, number][] {
  // an arc facing the camera, two staggered rows
  const out: [number, number][] = [];
  for (let i = 0; i < n; i++) {
    const t = (i + 0.5) / n, a = Math.PI * (0.15 + 0.7 * t);
    const r = 6.2 + (i % 2 ? 1.1 : 0);
    out.push([Math.cos(a) * r, -Math.sin(a) * r * 0.55 - 1.2]);
  }
  return out;
}

function Stage({ budget, usedUnits }: { budget: number; usedUnits: number }) {
  const fill = Math.min(1, usedUnits / Math.max(budget, 1));
  const h = 0.06 + 2.6 * fill;
  const ref = useRef<THREE.Mesh>(null!);
  useFrame((_, dt) => { const k = 1 - Math.pow(0.002, dt); ref.current.scale.y += (h - ref.current.scale.y) * k; ref.current.position.y = ref.current.scale.y / 2 + 0.05; });
  return (
    <group>
      {/* approval stage */}
      <mesh position={[0, -0.02, 2.2]} receiveShadow><boxGeometry args={[15, 0.08, 4.4]} /><meshStandardMaterial color="#141C33" roughness={0.6} metalness={0.2} /></mesh>
      <mesh position={[0, 0.03, 2.2]} rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[14.6, 4]} /><meshBasicMaterial color="#F2B84B" transparent opacity={0.06} /></mesh>
      <Line points={[[-7.3, 0.05, 0.02], [7.3, 0.05, 0.02]]} color="#F2B84B" lineWidth={1.4} transparent opacity={0.6} />
      <spotLight position={[0, 9, 2.2]} angle={0.55} penumbra={0.7} intensity={2.2} color="#FFE2A8" castShadow target-position={[0, 0, 2.2]} />
      {/* vault gauge */}
      <group position={[9.2, 0, 1.6]}>
        <mesh position={[0, 1.4, 0]}><cylinderGeometry args={[0.55, 0.55, 2.8, 32, 1, true]} /><meshPhysicalMaterial color="#5EE7F0" transparent opacity={0.12} roughness={0.1} side={THREE.DoubleSide} /></mesh>
        <mesh ref={ref} position={[0, 0.05, 0]} scale={[1, 0.06, 1]}><cylinderGeometry args={[0.5, 0.5, 1, 32]} /><meshStandardMaterial color="#F2B84B" emissive="#7A5E27" metalness={0.6} roughness={0.35} /></mesh>
        <mesh position={[0, 2.82, 0]} rotation={[-Math.PI / 2, 0, 0]}><ringGeometry args={[0.5, 0.58, 40]} /><meshBasicMaterial color="#5EE7F0" transparent opacity={0.8} side={THREE.DoubleSide} /></mesh>
        <mesh position={[0, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[0.7, 40]} /><meshBasicMaterial color="#1F5F66" /></mesh>
      </group>
    </group>
  );
}

function Couplings({ P, x, homes, gOn, lOn }: { P: Problem; x: Bits; homes: [number, number][]; gOn: boolean; lOn: boolean }) {
  const segs = useMemo(() => {
    const s: { a: [number, number, number]; b: [number, number, number]; kind: "sector" | "group" }[] = [];
    for (let i = 0; i < P.n; i++) for (let j = i + 1; j < P.n; j++) {
      if (!(x[i] && x[j])) continue;
      const same = gOn && P.pool[i].sector === P.pool[j].sector, opp = lOn && P.pool[i].group !== P.pool[j].group;
      if (!(same || opp)) continue;
      s.push({ a: [homes[i][0], 1.3, homes[i][1] + 2.6], b: [homes[j][0], 1.3, homes[j][1] + 2.6], kind: same ? "sector" : "group" });
    }
    return s;
  }, [P, x, homes, gOn, lOn]);
  return <>{segs.map((s, k) => <Line key={k} points={[s.a, s.b]} color={s.kind === "sector" ? "#5EE7F0" : "#C9A0FF"} lineWidth={1.6} transparent opacity={0.55} />)}</>;
}

function CameraRig({ solveTick, reduced }: { solveTick: number; reduced: boolean }) {
  const { camera } = useThree();
  useEffect(() => {
    if (reduced || solveTick === 0) return;
    // a short push-in on each solve, then ease back
    gsap.fromTo(camera.position, { z: camera.position.z }, { z: camera.position.z - 1.2, duration: 0.35, yoyo: true, repeat: 1, ease: "power2.inOut" });
  }, [solveTick, camera, reduced]);
  return null;
}

export function Scene({ P, x, manual, gOn, lOn, solveTick, onPick, reduced }: SceneProps) {
  const homes = useMemo(() => layout(P.n), [P.n]);
  const shown = manual ?? x;
  return (
    <Canvas shadows dpr={[1, 2]} camera={{ position: [0, 6.5, 14], fov: 42, near: 0.1, far: 120 }} gl={{ antialias: true }}>
      <color attach="background" args={["#0B1020"]} />
      <fog attach="fog" args={["#0B1020", 18, 40]} />
      <ambientLight intensity={0.55} color="#8EA0CC" />
      <directionalLight position={[6, 12, 8]} intensity={1.1} color="#FFF2DA" castShadow shadow-mapSize={[2048, 2048]} />
      <pointLight position={[-9, 5, -6]} intensity={0.8} color="#5EE7F0" />
      <Grid position={[0, 0, 0]} args={[60, 60]} cellSize={1} cellThickness={0.6} cellColor="#1E2A47" sectionSize={5} sectionThickness={1} sectionColor="#2A3A63" fadeDistance={34} fadeStrength={1.4} infiniteGrid />
      <ContactShadows position={[0, 0.001, 0]} opacity={0.55} scale={40} blur={2.4} far={8} color="#000000" />
      <Stage budget={P.budget} usedUnits={used(P, shown)} />
      {P.pool.map((p, i) => (
        <Person key={p.id} person={p} index={i} home={homes[i]} funded={!!x[i] && !manual} selected={!!manual?.[i]} interactive={!!manual} onClick={() => onPick(i)} />
      ))}
      <Couplings P={P} x={shown} homes={homes} gOn={gOn} lOn={lOn} />
      <CameraRig solveTick={solveTick} reduced={reduced} />
      <OrbitControls enablePan={false} minDistance={8} maxDistance={24} minPolarAngle={0.5} maxPolarAngle={1.35} autoRotate={!reduced} autoRotateSpeed={0.35} target={[0, 1, 0.5]} />
    </Canvas>
  );
}
