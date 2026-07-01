<template>
  <div class="ascii-container" @mousemove="onMouseMove">
    <div class="ascii-header-tag">
      <span class="ascii-dot"></span>
      <span class="ascii-label">SIMULATION PROSPECTIVE • 577 SIÈGES ASCII ORB</span>
    </div>

    <!-- Live ASCII 3D Render Canvas -->
    <pre ref="asciiPre" class="ascii-render-box" :style="{ color: textColor }">{{ asciiFrame }}</pre>

    <div class="ascii-footer-hint">
      <span>[ Moteur de rendu 3D Pointillisme ASCII • Déplacez le curseur pour orienter la sphère ]</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  textColor: {
    type: String,
    default: '#000000'
  }
})

const asciiPre = ref(null)
const asciiFrame = ref('')

// ASCII luminance palette from dark to bright (dithered pointillism style)
const chars = " ·.:;+=xX$&"

let animationFrameId = null
let angleA = 0
let angleB = 0
let targetSpeedA = 0.02
let targetSpeedB = 0.01

const onMouseMove = (e) => {
  if (!asciiPre.value) return
  const rect = asciiPre.value.getBoundingClientRect()
  const centerX = rect.left + rect.width / 2
  const centerY = rect.top + rect.height / 2
  
  // Calculate relative cursor position from center (-1 to 1)
  const relX = (e.clientX - centerX) / (rect.width / 2)
  const relY = (e.clientY - centerY) / (rect.height / 2)
  
  targetSpeedB = relX * 0.05
  targetSpeedA = -relY * 0.05
}

const renderAsciiSphere = () => {
  // Grid resolution
  const width = 64
  const height = 32
  
  // Buffers
  const zBuffer = new Array(width * height).fill(-Infinity)
  const output = new Array(width * height).fill(' ')
  
  // Sphere parameters
  const R = 1.4 // Sphere radius
  const K2 = 5  // Distance from viewer
  const K1 = width * K2 * 0.38 // Projection scaling factor
  
  // Angles calculation
  const cosA = Math.cos(angleA)
  const sinA = Math.sin(angleA)
  const cosB = Math.cos(angleB)
  const sinB = Math.sin(angleB)
  
  // Loop over theta and phi
  for (let theta = 0; theta < 2 * Math.PI; theta += 0.06) {
    const cosTheta = Math.cos(theta)
    const sinTheta = Math.sin(theta)
    
    for (let phi = 0; phi < Math.PI; phi += 0.06) {
      const cosPhi = Math.cos(phi)
      const sinPhi = Math.sin(phi)
      
      // 3D coordinates of point on sphere (centered at origin)
      const x = R * sinPhi * cosTheta
      const y = R * sinPhi * sinTheta
      const z = R * cosPhi
      
      // Rotate around X axis by A and Y axis by B
      // First rotate around X axis (angle A)
      const y1 = y * cosA - z * sinA
      const z1 = y * sinA + z * cosA
      
      // Then rotate around Y axis (angle B)
      const x2 = x * cosB + z1 * sinB
      const y2 = y1
      const z2 = -x * sinB + z1 * cosB + K2
      
      const ooz = 1 / z2
      
      // 2D projection
      const xp = Math.floor(width / 2 + K1 * ooz * x2)
      const yp = Math.floor(height / 2 - K1 * ooz * y2 * 0.55) // 0.55 corrects aspect ratio of font characters
      
      // Surface normal vector rotated
      const nx = sinPhi * cosTheta
      const ny = sinPhi * sinTheta
      const nz = cosPhi
      
      const ny1 = ny * cosA - nz * sinA
      const nz1 = ny * sinA + nz * cosA
      const nx2 = nx * cosB + nz1 * sinB
      const ny2 = ny1
      const nz2 = -nx * sinB + nz1 * cosB
      
      // Light source vector pointing from top-right-front (0.5, 0.7, -0.5)
      const lx = 0.57
      const ly = 0.57
      const lz = -0.57
      
      // Luminance (dot product of normal and light direction)
      const L = nx2 * lx + ny2 * ly + nz2 * lz
      
      if (L > 0) {
        if (xp >= 0 && xp < width && yp >= 0 && yp < height) {
          const idx = xp + yp * width
          if (ooz > zBuffer[idx]) {
            zBuffer[idx] = ooz
            const luminanceIdx = Math.floor(L * (chars.length - 1))
            output[idx] = chars[luminanceIdx] || chars[chars.length - 1]
          }
        }
      }
    }
  }
  
  // Format into rows
  let result = ''
  for (let j = 0; j < height; j++) {
    result += output.slice(j * width, (j + 1) * width).join('') + '\n'
  }
  
  asciiFrame.value = result
  
  // Advance rotation
  angleA += targetSpeedA
  angleB += targetSpeedB
  
  // Damping back to idle rotation speed
  targetSpeedA += (0.015 - targetSpeedA) * 0.05
  targetSpeedB += (0.025 - targetSpeedB) * 0.05
  
  animationFrameId = requestAnimationFrame(renderAsciiSphere)
}

onMounted(() => {
  renderAsciiSphere()
})

onUnmounted(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
})
</script>

<style scoped>
.ascii-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: 16px auto 32px;
  user-select: none;
  cursor: grab;
}

.ascii-container:active {
  cursor: grabbing;
}

.ascii-header-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  color: #64748B;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  padding: 4px 14px;
  border-radius: 9999px;
  margin-bottom: 12px;
}

.ascii-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #000000;
  box-shadow: 0 0 6px rgba(0, 0, 0, 0.4);
}

.ascii-render-box {
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 9.5px;
  line-height: 9.5px;
  letter-spacing: 1.5px;
  font-weight: 700;
  text-align: center;
  overflow: hidden;
  margin: 0;
  padding: 16px 24px;
  background: transparent;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.ascii-container:hover .ascii-render-box {
  transform: scale(1.03);
}

.ascii-footer-hint {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #94A3B8;
  margin-top: 8px;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.ascii-container:hover .ascii-footer-hint {
  opacity: 1;
  color: #000000;
}
</style>
