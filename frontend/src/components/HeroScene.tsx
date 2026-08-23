import {Canvas, useFrame} from '@react-three/fiber';
import {Float, Line, Sparkles} from '@react-three/drei';
import {useRef} from 'react';
import type {Group} from 'three';

function PatchField() {
  const group = useRef<Group>(null);
  useFrame(({clock, pointer}) => {
    if (!group.current) return;
    group.current.rotation.y = pointer.x * .18;
    group.current.rotation.x = -pointer.y * .12;
    group.current.position.y = Math.sin(clock.elapsedTime * .45) * .06;
  });
  const patches = Array.from({length: 49}, (_, index) => ({
    x: (index % 7 - 3) * .39,
    y: (3 - Math.floor(index / 7)) * .39,
    z: Math.sin(index * 1.7) * .08,
  }));
  return <group ref={group}>
    {patches.map((patch, index) => <mesh key={index} position={[patch.x, patch.y, patch.z]}>
      <boxGeometry args={[.34, .34, .025]}/>
      <meshStandardMaterial color={index % 8 === 0 ? '#d946ef' : '#6d28d9'} emissive={index % 8 === 0 ? '#d946ef' : '#7c3aed'} emissiveIntensity={index % 8 === 0 ? 1.5 : .28} transparent opacity={.72}/>
    </mesh>)}
    <Float speed={2.5} rotationIntensity={.4}><mesh position={[0, 0, .8]}><icosahedronGeometry args={[.18, 2]}/><meshStandardMaterial color="#e879f9" emissive="#a855f7" emissiveIntensity={4}/></mesh></Float>
    {[-1.1, 0, 1.1].map((y) => <Line key={y} points={[[-1.9, y, 0], [0, y * .3, .8], [1.9, y, 0]]} color="#c084fc" transparent opacity={.28} lineWidth={.7}/>)}
  </group>;
}

export function HeroScene() {
  return <div className="hero-canvas" aria-label="Illustrative Vision Transformer patch field">
    <Canvas camera={{position: [0, 0, 5.2], fov: 42}} dpr={[1, 1.5]}>
      <ambientLight intensity={.5}/><pointLight position={[2, 2, 4]} color="#d946ef" intensity={12}/><pointLight position={[-3, -1, 3]} color="#22d3ee" intensity={7}/>
      <PatchField/><Sparkles count={35} scale={6} size={1.2} speed={.25} color="#c084fc"/>
    </Canvas>
  </div>;
}

