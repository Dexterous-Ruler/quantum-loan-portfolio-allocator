/** A stylised 3D human figure built from primitives — no external model files, renders
 *  identically everywhere. Poses and positions are lerped every frame toward a target state:
 *  a funded person steps forward onto the stage and raises their arms; a declined person steps
 *  back into shadow. Outfit colour encodes segment; the floor glow encodes default risk. */
import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import type { Applicant } from "../data/applicants";

export const SECTOR_COLOR: Record<string, string> = {
  university: "#4F8CF0", graduate: "#8B6CFF", "high-school": "#2FB7A3", other: "#8E97AE",
};
const SKIN = ["#F1C6A5", "#D9A57C", "#B87A4E", "#8B5A38", "#F5D3B7"];
const HAIR = ["#1B1B22", "#3B2A1E", "#5A3A21", "#0F0F14", "#6E4A2C"];
const GOLD = new THREE.Color("#F2B84B"), DIM = new THREE.Color("#3A4360");

export interface PersonProps {
  person: Applicant; index: number; home: [number, number]; funded: boolean; selected: boolean;
  interactive: boolean; onClick?: () => void;
}

export function Person({ person, index, home, funded, selected, interactive, onClick }: PersonProps) {
  const root = useRef<THREE.Group>(null!);
  const armL = useRef<THREE.Group>(null!), armR = useRef<THREE.Group>(null!);
  const body = useRef<THREE.MeshStandardMaterial>(null!);
  const ring = useRef<THREE.MeshBasicMaterial>(null!);
  const glow = useRef<THREE.PointLight>(null!);
  const [hover, setHover] = useState(false);

  const look = useMemo(() => ({
    skin: SKIN[index % SKIN.length], hair: HAIR[(index * 7) % HAIR.length],
    outfit: new THREE.Color(SECTOR_COLOR[person.sector] ?? SECTOR_COLOR.other),
    height: person.group === "female" ? 0.97 : 1.03, phase: Math.random() * Math.PI * 2,
    longHair: person.group === "female",
  }), [index, person]);

  const on = funded || selected;
  // Step forward onto the stage when funded; stand back when declined.
  const targetZ = home[1] + (on ? 2.6 : 0);
  const targetArm = on ? -2.35 : 0.18;

  useFrame((state, dt) => {
    const k = 1 - Math.pow(0.001, dt);          // frame-rate independent easing
    const g = root.current;
    g.position.z += (targetZ - g.position.z) * k;
    g.position.y = (on ? 0.02 : 0) + Math.sin(state.clock.elapsedTime * 1.4 + look.phase) * 0.012;
    armL.current.rotation.z += (targetArm - armL.current.rotation.z) * k;
    armR.current.rotation.z += (-targetArm - armR.current.rotation.z) * k;
    const tgtCol = on ? look.outfit : look.outfit.clone().lerp(DIM, 0.55);
    body.current.color.lerp(tgtCol, k);
    body.current.emissive.lerp(on ? GOLD.clone().multiplyScalar(0.25) : new THREE.Color(0, 0, 0), k);
    const ringCol = on ? GOLD : new THREE.Color("#E5533D");
    ring.current.color.lerp(ringCol, k);
    ring.current.opacity += ((on ? 0.85 : Math.min(0.7, person.p * 3)) - ring.current.opacity) * k;
    glow.current.intensity += ((on ? 1.6 : 0) - glow.current.intensity) * k;
    g.scale.setScalar(THREE.MathUtils.lerp(g.scale.x, hover ? 1.06 : 1, k));
  });

  const h = look.height;
  return (
    <group ref={root} position={[home[0], 0, home[1]]}
      onPointerOver={(e) => { e.stopPropagation(); setHover(true); document.body.style.cursor = interactive ? "pointer" : "default"; }}
      onPointerOut={() => { setHover(false); document.body.style.cursor = "default"; }}
      onClick={(e) => { e.stopPropagation(); if (interactive) onClick?.(); }}>

      {/* floor ring: risk aura (red) or approval ring (gold) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.012, 0]}>
        <ringGeometry args={[0.42, 0.6, 48]} />
        <meshBasicMaterial ref={ring} color="#E5533D" transparent opacity={0.3} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
      <pointLight ref={glow} color="#F2B84B" intensity={0} distance={3.2} position={[0, 2.3, 0]} />

      <group scale={[1, h, 1]}>
        {/* legs */}
        <mesh position={[-0.14, 0.42, 0]} castShadow><capsuleGeometry args={[0.1, 0.62, 6, 12]} /><meshStandardMaterial color="#232A40" roughness={0.9} /></mesh>
        <mesh position={[0.14, 0.42, 0]} castShadow><capsuleGeometry args={[0.1, 0.62, 6, 12]} /><meshStandardMaterial color="#232A40" roughness={0.9} /></mesh>
        {/* torso (outfit = segment colour) */}
        <mesh position={[0, 1.12, 0]} castShadow>
          <capsuleGeometry args={[0.24, 0.5, 8, 16]} />
          <meshStandardMaterial ref={body} color={look.outfit} roughness={0.55} metalness={0.05} />
        </mesh>
        {/* arms (pivot at shoulder) */}
        <group ref={armL} position={[-0.33, 1.36, 0]}>
          <mesh position={[0, -0.3, 0]} castShadow><capsuleGeometry args={[0.075, 0.5, 6, 12]} /><meshStandardMaterial color={look.skin} roughness={0.8} /></mesh>
        </group>
        <group ref={armR} position={[0.33, 1.36, 0]}>
          <mesh position={[0, -0.3, 0]} castShadow><capsuleGeometry args={[0.075, 0.5, 6, 12]} /><meshStandardMaterial color={look.skin} roughness={0.8} /></mesh>
        </group>
        {/* head + hair */}
        <mesh position={[0, 1.75, 0]} castShadow><sphereGeometry args={[0.2, 24, 24]} /><meshStandardMaterial color={look.skin} roughness={0.7} /></mesh>
        <mesh position={[0, look.longHair ? 1.78 : 1.83, -0.02]}>
          <sphereGeometry args={[look.longHair ? 0.225 : 0.205, 24, 24, 0, Math.PI * 2, 0, look.longHair ? Math.PI * 0.72 : Math.PI * 0.5]} />
          <meshStandardMaterial color={look.hair} roughness={0.85} />
        </mesh>
      </group>

      {/* capital units: a stack of coins above the head, one per NT$20k unit */}
      <group position={[0, 2.1 * h + 0.15, 0]}>
        {Array.from({ length: person.units }).map((_, i) => (
          <mesh key={i} position={[0, i * 0.075, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.13, 0.13, 0.05, 20]} />
            <meshStandardMaterial color={on ? "#F2B84B" : "#6B5A2E"} metalness={0.7} roughness={0.3} emissive={on ? "#7A5E27" : "#000000"} />
          </mesh>
        ))}
      </group>

      {hover && (
        <Html position={[0, 2.1 * h + 0.2 + person.units * 0.075, 0]} center distanceFactor={10} style={{ pointerEvents: "none" }}>
          <div className="tip">
            <div className="tip-h"><b>#{person.id}</b><span className={"pill " + (on ? "ok" : "")}>{on ? "FUNDED" : "declined"}</span></div>
            <div className="tip-r"><span>P(default)</span><b>{(person.p * 100).toFixed(1)}%</b></div>
            <div className="tip-r"><span>Expected value</span><b>NT${person.ev.toLocaleString()}</b></div>
            <div className="tip-r"><span>Exposure</span><b>NT${person.exposure.toLocaleString()}</b></div>
            <div className="tip-r"><span>Capital units</span><b>{person.units}</b></div>
            <div className="tip-r"><span>Segment · group</span><b>{person.sector} · {person.group}</b></div>
          </div>
        </Html>
      )}
    </group>
  );
}
