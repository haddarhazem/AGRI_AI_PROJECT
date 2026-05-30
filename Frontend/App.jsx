import React, { useState, useEffect, useRef, useReducer } from 'react';
import * as THREE from 'three';

// --- STYLES INJECTION ---
const globalStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&family=Rajdhani:wght@500;700&display=swap');

  :root {
    --bg-dark: #080C10;
    --accent-lime: #A8FF3E;
    --accent-cyan: #00D4FF;
    --accent-amber: #FFB800;
    --accent-red: #FF4444;
  }

  body {
    background-color: var(--bg-dark);
    color: #ffffff;
    font-family: 'Inter', sans-serif;
    margin: 0;
    padding: 0;
    overflow-x: hidden;
    position: relative;
  }

  /* Scanline effect */
  body::before {
    content: " ";
    display: block;
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
    z-index: 2;
    background-size: 100% 2px, 3px 100%;
    pointer-events: none;
    opacity: 0.4;
  }

  h1, h2, h3, h4, h5, h6 {
    font-family: 'Rajdhani', sans-serif;
    text-transform: uppercase;
    letter-spacing: 2px;
  }

  .mono {
    font-family: 'JetBrains Mono', monospace;
  }

  .glass-card {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(168, 255, 62, 0.15);
    backdrop-filter: blur(12px);
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    position: relative;
    overflow: hidden;
  }

  .glass-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent-lime), transparent);
    opacity: 0.5;
  }

  .btn-primary {
    background: transparent;
    color: var(--accent-lime);
    border: 1px solid var(--accent-lime);
    padding: 12px 24px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 16px;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.2s ease;
    text-transform: uppercase;
    position: relative;
    overflow: hidden;
  }
  
  .btn-primary:hover:not(:disabled) {
    background: rgba(168, 255, 62, 0.1);
    box-shadow: 0 0 15px rgba(168, 255, 62, 0.3);
  }

  .btn-primary:disabled {
    border-color: #444;
    color: #666;
    cursor: not-allowed;
  }

  .text-lime { color: var(--accent-lime); }
  .text-cyan { color: var(--accent-cyan); }
  .text-amber { color: var(--accent-amber); }
  .text-red { color: var(--accent-red); }

  .bg-lime { background-color: var(--accent-lime); }

  .animate-slide-up {
    animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }

  @keyframes slideUp {
    from { transform: translateY(40px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }

  @keyframes pulse {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(168, 255, 62, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(168, 255, 62, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(168, 255, 62, 0); }
  }

  .glowing-dot {
    width: 8px;
    height: 8px;
    background-color: var(--accent-lime);
    border-radius: 50%;
    display: inline-block;
    animation: pulse 2s infinite;
    margin-right: 12px;
  }
`;

// --- API INTEGRATION (uses Vite proxy: /api/*) ---
const fetchClimateData = async (lat, lon, season) => {
  const response = await fetch('/api/climate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lat, lon, season })
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Climate fetch failed');
  }

  const data = await response.json();
  return {
    elevation:           data.elevation,
    temperature:         data.temperature,
    humidity:            data.humidity,
    rainfall:            data.rainfall,
    isOutOfDistribution: data.is_out_of_distribution,
    warnings:            data.warnings,
    source:              data.source,
    seasonName:          data.season_name,
    seasonLabel:         data.season_label,
  };
};

const runAIPrediction = async (climate) => {
  const response = await fetch('/api/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      temperature: climate.temperature,
      humidity:    climate.humidity,
      rainfall:    climate.rainfall,
    })
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Prediction failed');
  }

  const data = await response.json();
  return {
    crop:             data.crop,
    confidence:       data.confidence,
    isLowConfidence:  data.is_low_confidence,
    alternatives:     data.alternatives.map(a => ({ crop: a.crop, conf: a.confidence, confidence: a.confidence })),
  };
};

const fetchPrescription = async (crop, soilValues) => {
  const response = await fetch('/api/prescription', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      crop: crop,
      n:    parseFloat(soilValues.n),
      p:    parseFloat(soilValues.p),
      k:    parseFloat(soilValues.k),
      ph:   parseFloat(soilValues.ph),
    })
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Prescription failed');
  }

  const data = await response.json();
  return {
    ideal:        data.ideal,
    deltas:       data.deltas,
    prescription: data.prescription,
  };
};

// --- KML GENERATOR ---
const generateKML = (state) => {
  const { coordinates, season, climate, prediction, prescription } = state;
  const seasonNames = { '1': 'Spring-Summer', '2': 'Autumn-Winter', '3': 'Full-Year' };
  
  return `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Placemark>
    <name>${prediction.crop.toUpperCase()} — ${seasonNames[season]}</name>
    <description>
      <![CDATA[
      <h2>Recommended Crop: ${prediction.crop.toUpperCase()}</h2>
      <p><b>Confidence:</b> ${(prediction.confidence * 100).toFixed(1)}%</p>
      <hr>
      <h3>Climate Data</h3>
      <ul>
        <li><b>Temperature:</b> ${climate.temperature.toFixed(1)}°C</li>
        <li><b>Humidity:</b> ${climate.humidity.toFixed(1)}%</li>
        <li><b>Rainfall:</b> ${climate.rainfall.toFixed(1)}mm/yr</li>
        <li><b>Elevation:</b> ${climate.elevation}m</li>
      </ul>
      <hr>
      <h3>Soil Prescription</h3>
      <p>${prescription.prescription.nitrogen.message}</p>
      <p>${prescription.prescription.phosphorus.message}</p>
      <p>${prescription.prescription.potassium.message}</p>
      <p>${prescription.prescription.ph.message}</p>
      ]]>
    </description>
    <Point>
      <coordinates>${coordinates.lon},${coordinates.lat},0</coordinates>
    </Point>
  </Placemark>
</kml>`;
};

// --- ANIMATED COUNTER COMPONENT ---
const NumberCounter = ({ value, formatter = (v) => v.toFixed(1), duration = 1000 }) => {
  const [displayedValue, setDisplayedValue] = useState(0);
  
  useEffect(() => {
    let start = null;
    const initialValue = 0;
    const targetValue = value || 0;
    
    const step = (timestamp) => {
      if (!start) start = timestamp;
      const progress = Math.min((timestamp - start) / duration, 1);
      setDisplayedValue(initialValue + progress * (targetValue - initialValue));
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };
    window.requestAnimationFrame(step);
  }, [value, duration]);

  return <span>{formatter(displayedValue)}</span>;
};

// --- THREE.JS COMPONENTS ---
const Globe3D = ({ lat, lon }) => {
  const mountRef = useRef(null);

  useEffect(() => {
    const w = mountRef.current.clientWidth || 400;
    const h = 400;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(w, h);
    mountRef.current.innerHTML = '';
    mountRef.current.appendChild(renderer.domElement);

    const geo = new THREE.SphereGeometry(2, 32, 32);
    const mat = new THREE.MeshBasicMaterial({ color: 0x011a00 });
    const wireMat = new THREE.MeshBasicMaterial({ color: 0xA8FF3E, wireframe: true, transparent: true, opacity: 0.15 });
    const sphere = new THREE.Mesh(geo, mat);
    const wire = new THREE.Mesh(geo, wireMat);
    scene.add(sphere);
    scene.add(wire);

    let marker = null;
    let markerRing = null;

    if (lat !== null && lon !== null) {
      const phi = (90 - lat) * (Math.PI / 180);
      const theta = (lon + 180) * (Math.PI / 180);
      
      const x = -(2 * Math.sin(phi) * Math.cos(theta));
      const y = 2 * Math.cos(phi);
      const z = 2 * Math.sin(phi) * Math.sin(theta);
      
      const mGeo = new THREE.SphereGeometry(0.05, 8, 8);
      const mMat = new THREE.MeshBasicMaterial({ color: 0x00D4FF });
      marker = new THREE.Mesh(mGeo, mMat);
      marker.position.set(x, y, z);
      scene.add(marker);

      const ringGeo = new THREE.RingGeometry(0.06, 0.08, 16);
      const ringMat = new THREE.MeshBasicMaterial({ color: 0xA8FF3E, side: THREE.DoubleSide });
      markerRing = new THREE.Mesh(ringGeo, ringMat);
      markerRing.position.set(x, y, z);
      markerRing.lookAt(x*2, y*2, z*2);
      scene.add(markerRing);

      const targetRotY = theta - Math.PI / 2;
      const targetRotX = (Math.PI / 2) - phi;

      // Tween rotation
      const animateTarget = () => {
        scene.rotation.y += (targetRotY - scene.rotation.y) * 0.05;
        scene.rotation.x += (targetRotX - scene.rotation.x) * 0.05;
      }
      
      const renderSingle = () => {
        requestAnimationFrame(renderSingle);
        animateTarget();
        if (markerRing) {
          markerRing.scale.x = 1 + (Math.sin(Date.now() * 0.005) * 0.5 + 0.5);
          markerRing.scale.y = 1 + (Math.sin(Date.now() * 0.005) * 0.5 + 0.5);
          markerRing.material.opacity = 1 - (Math.sin(Date.now() * 0.005) * 0.5 + 0.5);
          markerRing.material.transparent = true;
        }
        renderer.render(scene, camera);
      };
      renderSingle();
    } else {
      const renderIdle = () => {
        requestAnimationFrame(renderIdle);
        sphere.rotation.y += 0.005;
        wire.rotation.y += 0.005;
        renderer.render(scene, camera);
      };
      renderIdle();
    }

    camera.position.z = 6;

    return () => {
      renderer.dispose();
    };
  }, [lat, lon]);

  return <div ref={mountRef} style={{ width: '100%', height: '400px', cursor: 'grab' }} />;
};

const BarChart3D = ({ prediction }) => {
  const mountRef = useRef(null);

  useEffect(() => {
    if (!prediction || !prediction.crop) return;
    
    const w = mountRef.current.clientWidth || 300;
    const h = 200;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(w, h);
    mountRef.current.innerHTML = '';
    mountRef.current.appendChild(renderer.domElement);

    const group = new THREE.Group();
    scene.add(group);

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(5, 5),
      new THREE.MeshBasicMaterial({ color: 0x112211, side: THREE.DoubleSide, transparent: true, opacity: 0.3 })
    );
    ground.rotation.x = Math.PI / 2;
    group.add(ground);

    const items = [
      { crop: prediction.crop, conf: prediction.confidence },
      ...prediction.alternatives
    ];

    items.forEach((item, i) => {
      const height = item.conf * 3;
      const col = new THREE.Color().setHSL(item.conf * 0.3, 1, 0.5); // red to green
      const geo = new THREE.BoxGeometry(0.4, 0.01, 0.4); // animate from 0.01
      const mat = new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.8 });
      const mesh = new THREE.Mesh(geo, mat);
      
      mesh.position.set(-1 + i * 1, 0, 0);
      
      // Store target height for animation
      mesh.userData.targetHeight = height;
      group.add(mesh);
    });

    camera.position.set(0, 3, 5);
    camera.lookAt(0, 0, 0);

    const animate = () => {
      requestAnimationFrame(animate);
      group.rotation.y += 0.005;
      
      group.children.forEach(c => {
        if (c.userData.targetHeight && c.scale.y < c.userData.targetHeight * 100) {
          c.scale.y += (c.userData.targetHeight * 100 - c.scale.y) * 0.1;
          c.position.y = (c.geometry.parameters.height * c.scale.y) / 2;
        }
      });
      
      renderer.render(scene, camera);
    };
    animate();

    return () => renderer.dispose();
  }, [prediction]);

  return <div ref={mountRef} style={{ width: '100%', height: '200px' }} />;
};

const RadarChart3D = ({ userSoil, idealSoil }) => {
  const mountRef = useRef(null);

  useEffect(() => {
    if (!userSoil || !idealSoil) return;
    
    const w = mountRef.current.clientWidth || 300;
    const h = 300;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(w, h);
    mountRef.current.innerHTML = '';
    mountRef.current.appendChild(renderer.domElement);

    const group = new THREE.Group();
    scene.add(group);

    // Axes
    const axesGeo = new THREE.BufferGeometry();
    const axesVerts = new Float32Array([
      0,0,0, 0,2,0, // N
      0,0,0, 2,0,0, // P
      0,0,0, 0,-2,0, // K
      0,0,0, -2,0,0  // pH
    ]);
    axesGeo.setAttribute('position', new THREE.BufferAttribute(axesVerts, 3));
    const axesLine = new THREE.LineSegments(axesGeo, new THREE.LineBasicMaterial({ color: 0x444444 }));
    group.add(axesLine);

    // Scale factors
    const maxN = 100, maxP = 100, maxK = 100, maxPh = 14;
    
    const createPolygon = (values, color) => {
      const pts = [
        new THREE.Vector3(0, (values.n / maxN) * 2, 0),
        new THREE.Vector3((values.p / maxP) * 2, 0, 0),
        new THREE.Vector3(0, -(values.k / maxK) * 2, 0),
        new THREE.Vector3(-(values.ph / maxPh) * 2, 0, 0),
      ];
      pts.push(pts[0]); // close loop
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      return new THREE.Line(geo, new THREE.LineBasicMaterial({ color, linewidth: 2 }));
    };

    const idealPoly = createPolygon(idealSoil, 0xA8FF3E);
    const userPoly = createPolygon(userSoil, 0x00D4FF);
    group.add(idealPoly);
    group.add(userPoly);

    camera.position.set(0, 0, 6);
    group.rotation.x = Math.PI / 8; // slight 3D tilt
    group.rotation.y = -Math.PI / 8;

    const animate = () => {
      requestAnimationFrame(animate);
      group.rotation.y += 0.005;
      renderer.render(scene, camera);
    };
    animate();

    return () => renderer.dispose();
  }, [userSoil, idealSoil]);

  return <div ref={mountRef} style={{ width: '100%', height: '300px' }} />;
};

// --- APP COMPONENT ---
export default function GeoAIApp() {
  const [state, setState] = useState({
    step: 0,
    coordinates: { lat: null, lon: null },
    season: null,
    climate: { elevation: null, temperature: null, humidity: null, rainfall: null },
    prediction: { crop: null, confidence: null, alternatives: [], isLowConfidence: false },
    soil: { n: '', p: '', k: '', ph: '' },
    prescription: null
  });

  const [isLoading, setIsLoading] = useState(false);
  const [loadingLines, setLoadingLines] = useState([]);
  const [coordInput, setCoordInput] = useState('');
  const [backendOffline, setBackendOffline] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    fetch('/api/health')
      .then(r => r.json())
      .then(data => {
        if (data.status === 'online') {
          console.log(`✅ Backend online — ${data.crops_available} crops available`);
        }
      })
      .catch(() => {
        console.warn('⚠️ Backend not reachable. Start the API with: uvicorn api:app --reload --port 8000');
        setBackendOffline(true);
      });
  }, []);

  // Styles injected on mount
  useEffect(() => {
    const styleEl = document.createElement('style');
    styleEl.innerHTML = globalStyles;
    document.head.appendChild(styleEl);
    return () => document.head.removeChild(styleEl);
  }, []);

  const handleStart = () => setState(s => ({ ...s, step: 1 }));

  const handleCoordBlur = () => {
    const clean = coordInput.replace(/ /g, '').split(',');
    if (clean.length === 2 && !isNaN(clean[0]) && !isNaN(clean[1])) {
      setState(s => ({ ...s, coordinates: { lat: parseFloat(clean[0]), lon: parseFloat(clean[1]) } }));
    } else {
      setState(s => ({ ...s, coordinates: { lat: null, lon: null } }));
    }
  };

  const handleSeasonSelect = (id) => setState(s => ({ ...s, season: id }));

  const handleRunClimateEngine = async () => {
    setState(s => ({ ...s, step: 2 }));
    setIsLoading(true);
    setErrorMessage('');
    setLoadingLines(['[ ] Fetching elevation data (Copernicus DEM)...']);
    
    try {
      // Simulate step sequence for UI
      await new Promise(r => setTimeout(r, 600));
      const climateResult = await fetchClimateData(state.coordinates.lat, state.coordinates.lon, state.season);
      setLoadingLines(l => ["[✓] Fetching elevation data (Copernicus DEM)...", "[ ] Fetching 10-year seasonal climate data..."]);
      
      await new Promise(r => setTimeout(r, 800));
      setLoadingLines(l => [l[0], "[✓] Fetching 10-year seasonal climate data...", "[ ] Computing seasonal averages..."]);
      
      await new Promise(r => setTimeout(r, 800));
      setLoadingLines(l => [l[0], l[1], "[✓] Computing seasonal averages...", "[ ] Running AI prediction model..."]);
      
      const predResult = await runAIPrediction(climateResult);
      
      await new Promise(r => setTimeout(r, 1000));
      setIsLoading(false);
      setState(s => ({
        ...s,
        climate: climateResult,
        prediction: predResult
      }));
    } catch (error) {
      setIsLoading(false);
      setErrorMessage(error.message);
    }
  };

  const handleGeneratePrescription = async () => {
    setErrorMessage('');
    try {
      const result = await fetchPrescription(
        state.prediction.crop,
        state.soil
      );
      setState(s => ({
        ...s,
        step: 4,
        prescription: result
      }));
    } catch (error) {
      console.error('Prescription error:', error);
      setErrorMessage(error.message);
    }
  };

  const downloadKMLFile = () => {
    const content = generateKML(state);
    const blob = new Blob([content], { type: 'application/vnd.google-earth.kml+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `GeoTarget_${state.coordinates.lat}_${state.coordinates.lon}_${state.season}_GeoAI.kml`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyReport = () => {
    const text = `GEO-AI REPORT\nCrop: ${state.prediction.crop}\nConfidence: ${(state.prediction.confidence*100).toFixed(1)}%\n\n${state.prescription.prescription.nitrogen.message}\n${state.prescription.prescription.phosphorus.message}\n${state.prescription.prescription.potassium.message}\n${state.prescription.prescription.ph.message}`;
    navigator.clipboard.writeText(text);
    alert("Copied to clipboard!");
  };

  const handleReset = () => {
    setState({
      step: 0,
      coordinates: { lat: null, lon: null },
      season: null,
      climate: { elevation: null, temperature: null, humidity: null, rainfall: null },
      prediction: { crop: null, confidence: null, alternatives: [], isLowConfidence: false },
      soil: { n: '', p: '', k: '', ph: '' },
      prescription: null
    });
    setCoordInput('');
    setLoadingLines([]);
    setIsLoading(false);
    setErrorMessage('');
  };

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 20px', minHeight: '100vh', position: 'relative' }}>

      {backendOffline && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, zIndex: 9999,
          background: '#FF4444', color: '#fff',
          padding: '12px 24px', fontFamily: 'JetBrains Mono',
          fontSize: '13px', textAlign: 'center'
        }}>
          ⚠️ Backend offline — run: <code>uvicorn api:app --reload --port 8000</code> in your project folder
        </div>
      )}
      
      {/* RESTART BUTTON */}
      {state.step > 0 && (
        <button 
          onClick={handleReset} 
          className="btn-primary" 
          style={{ position: 'absolute', top: 20, right: 20, padding: '8px 16px', fontSize: 14, zIndex: 100 }}
        >
          [ RESTART MISSION ]
        </button>
      )}

      {/* STEP 0 */}
      {state.step === 0 && (
        <div className="animate-slide-up" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', marginTop: '10vh' }}>
          <Globe3D lat={null} lon={null} />
          <h1 style={{ fontSize: 48, margin: '20px 0 10px', color: '#fff', textShadow: '0 0 20px rgba(168,255,62,0.4)' }}>
            GEO-AI DECISION SUPPORT SYSTEM
          </h1>
          <p className="text-cyan mono" style={{ fontSize: 18, marginBottom: 40 }}>Climate Engine + Agronomist Engine</p>
          
          <div style={{ display: 'flex', gap: 40, marginBottom: 60 }}>
            <div className="glass-card" style={{ padding: '20px 40px' }}>
              <div style={{ fontSize: 32, color: 'var(--accent-lime)' }} className="mono"><NumberCounter value={32} formatter={v => Math.round(v)} /></div>
              <div style={{ fontSize: 12, opacity: 0.7, textTransform: 'uppercase' }}>Crops Analyzed</div>
            </div>
            <div className="glass-card" style={{ padding: '20px 40px' }}>
              <div style={{ fontSize: 32, color: 'var(--accent-cyan)' }} className="mono"><NumberCounter value={10} formatter={v => Math.round(v)} /></div>
              <div style={{ fontSize: 12, opacity: 0.7, textTransform: 'uppercase' }}>Yr Climate Data</div>
            </div>
          </div>

          <button className="btn-primary" onClick={handleStart} style={{ fontSize: 24, padding: '16px 48px' }}>
            <span className="glowing-dot"></span> INITIALIZE MISSION
          </button>
        </div>
      )}

      {/* STEP 1 */}
      {state.step >= 1 && (
        <div className={`glass-card ${state.step === 1 ? 'animate-slide-up' : ''}`} style={state.step > 1 ? { opacity: 0.5, height: 60, padding: '15px' } : {}}>
          <h2 className="text-lime" style={{ margin: 0 }}>// STEP 01 — TARGET ACQUISITION {state.step > 1 && '✅'}</h2>
          
          {state.step === 1 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) minmax(300px, 1fr)', gap: 40, marginTop: 30 }}>
              <div>
                <button className="btn-primary" onClick={() => window.open('https://www.google.com/maps', '_blank')} style={{ width: '100%', marginBottom: 20 }}>
                  [ OPEN GOOGLE MAPS ]
                </button>
                <div className="mono" style={{ background: 'rgba(0,0,0,0.5)', padding: 15, fontSize: 13, color: '#aaa', marginBottom: 20, whiteSpace: 'pre-wrap' }}>
                  {`1. Right-click anywhere on the map\n2. Click coordinates at top of menu\n3. Paste them below`}
                </div>
                <input 
                  type="text" 
                  value={coordInput}
                  onChange={e => setCoordInput(e.target.value)}
                  onBlur={handleCoordBlur}
                  placeholder="34.7405, 10.7603"
                  className="mono"
                  style={{ width: '100%', background: 'rgba(0,0,0,0.4)', border: `1px solid ${state.coordinates.lat ? 'var(--accent-lime)' : '#444'}`, color: '#fff', padding: 20, fontSize: 18, boxSizing: 'border-box' }}
                />
                {state.coordinates.lat && (
                  <div className="text-lime mono" style={{ marginTop: 15 }}>
                    <span className="glowing-dot"></span> LOCKED: LAT {state.coordinates.lat} / LON {state.coordinates.lon}
                  </div>
                )}
                
                <div style={{ marginTop: 20, border: '1px solid #333', background: '#000', borderRadius: 8, padding: 10 }}>
                  <Globe3D lat={state.coordinates.lat} lon={state.coordinates.lon} />
                </div>
              </div>

              <div>
                <h3 style={{ margin: '0 0 20px' }}>Select Season</h3>
                {[
                  { id: '1', icon: '☀️', title: 'Spring / Summer', desc: 'Mar – Aug | Rice, Maize' },
                  { id: '2', icon: '🍂', title: 'Autumn / Winter', desc: 'Sep – Feb | Lentil, Wheat' },
                  { id: '3', icon: '🌍', title: 'Full Year', desc: 'Jan – Dec | Mango, Coffee' }
                ].map(s => (
                  <div 
                    key={s.id}
                    onClick={() => handleSeasonSelect(s.id)}
                    style={{ 
                      padding: 24, background: state.season === s.id ? 'rgba(168,255,62,0.1)' : 'rgba(0,0,0,0.4)',
                      border: `1px solid ${state.season === s.id ? 'var(--accent-lime)' : '#333'}`, 
                      marginBottom: 15, cursor: 'pointer', borderRadius: 8, transition: 'all 0.2s'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 15 }}>
                      <span style={{ fontSize: 32 }}>{s.icon}</span>
                      <div>
                        <div style={{ fontSize: 18, fontWeight: 'bold' }}>{s.title}</div>
                        <div className="mono" style={{ fontSize: 13, color: '#aaa', marginTop: 5 }}>{s.desc}</div>
                      </div>
                    </div>
                  </div>
                ))}

                <button 
                  className="btn-primary" 
                  style={{ width: '100%', marginTop: 20 }}
                  disabled={!state.coordinates.lat || !state.season}
                  onClick={handleRunClimateEngine}
                >
                  [ LOCK TARGET & FETCH CLIMATE ]
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* STEP 2 */}
      {state.step >= 2 && (
        <div className={`glass-card ${state.step === 2 ? 'animate-slide-up' : ''}`} style={state.step > 2 ? { opacity: 0.5, height: 60, padding: '15px' } : {}}>
          <h2 className="text-cyan" style={{ margin: 0 }}>// STEP 02 — CLIMATE ENGINE {state.step > 2 && '✅'}</h2>
          
          {state.step === 2 && (
            <div style={{ marginTop: 30 }}>
              {errorMessage && (
                <div className="mono" style={{ background: 'rgba(255,68,68,0.1)', color: 'var(--accent-red)', padding: 15, borderLeft: '2px solid var(--accent-red)', marginBottom: 20 }}>
                  ⚠️ Error: {errorMessage}
                </div>
              )}
              {isLoading ? (
                <div className="mono" style={{ background: '#000', padding: 20, borderLeft: '2px solid var(--accent-cyan)' }}>
                  {loadingLines.map((line, i) => <div key={i} style={{ marginBottom: 10 }}>{line}</div>)}
                  <span className="glowing-dot" style={{ backgroundColor: 'var(--accent-cyan)' }}></span>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 40 }}>
                  
                  {/* Climate Metrics */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 15 }}>
                    {[
                      { l: 'Avg Temp', v: state.climate.temperature, u: '°C', i: '🌡️', c: 'rgba(255,68,68,0.1)' },
                      { l: 'Humidity', v: state.climate.humidity, u: '%', i: '💧', c: 'rgba(0,212,255,0.1)' },
                      { l: 'Rainfall', v: state.climate.rainfall, u: ' mm/yr', i: '🌧️', c: 'rgba(0,100,255,0.1)' },
                      { l: 'Elevation', v: state.climate.elevation, u: 'm', i: '⛰️', c: 'rgba(168,255,62,0.1)' }
                    ].map((m, i) => (
                      <div key={i} style={{ background: m.c, padding: 20, borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)' }}>
                        <div style={{ fontSize: 24, marginBottom: 10 }}>{m.i}</div>
                        <div className="mono" style={{ fontSize: 24, fontWeight: 'bold' }}>
                          <NumberCounter value={m.v} />{m.u}
                        </div>
                        <div style={{ fontSize: 11, textTransform: 'uppercase', color: '#aaa', marginTop: 5 }}>{m.l}</div>
                      </div>
                    ))}
                  </div>

                  {/* AI Prediction */}
                  <div className="mono" style={{ border: '1px solid var(--accent-cyan)', background: 'rgba(0,212,255,0.05)', padding: 24, borderRadius: 8 }}>
                    <div style={{ opacity: 0.7, marginBottom: 15 }}>┌─────────────────────────────────────────┐</div>
                    <div className="text-cyan" style={{ marginBottom: 20 }}>│  CLIMATE ENGINE RECOMMENDS              │</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 10 }}>
                      <div className="text-cyan">│  ██████</div>
                      <div style={{ fontFamily: 'Rajdhani', fontSize: 42, color: 'var(--accent-lime)', textTransform: 'uppercase', textShadow: '0 0 10px rgba(168,255,62,0.5)' }}>
                        {state.prediction.crop}
                      </div>
                    </div>
                    <div style={{ marginLeft: 100, marginBottom: 20 }}>│  Confidence: {(state.prediction.confidence * 100).toFixed(1)}%</div>
                    
                    <div className="text-cyan" style={{ marginBottom: 10 }}>│  Alternatives:</div>
                    {state.prediction.alternatives.map((alt, i) => (
                      <div key={i} style={{ marginLeft: 10, display: 'flex', justifyContent: 'space-between', maxWidth: 200, marginBottom: 5 }}>
                        <span>│  {i+2}. {alt.crop.charAt(0).toUpperCase() + alt.crop.slice(1)}</span>
                        <span>{(alt.conf * 100 || alt.confidence * 100).toFixed(1)}%</span>
                      </div>
                    ))}
                    <div style={{ opacity: 0.7, marginTop: 15 }}>└─────────────────────────────────────────┘</div>

                    {state.prediction.confidence < 0.5 && (
                      <div style={{ marginTop: 20, padding: 15, borderLeft: '3px solid var(--accent-amber)', background: 'rgba(255,184,0,0.1)' }}>
                        <div className="text-amber">⚠️ Low confidence ({(state.prediction.confidence * 100).toFixed(1)}%)</div>
                        <div style={{ fontSize: 13, color: '#ddd', marginTop: 10 }}>The climate matches a group of similar crops. Your soil data in Step 3 will determine the final answer.</div>
                      </div>
                    )}
                    
                    <div style={{ marginTop: 20 }}>
                      <BarChart3D prediction={state.prediction} />
                    </div>
                  </div>

                </div>
              )}
              {!isLoading && (
                <button className="btn-primary" onClick={() => setState(s => ({ ...s, step: 3 }))} style={{ marginTop: 30 }}>
                  [ PROCEED TO SOIL ANALYSIS ]
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* STEP 3 */}
      {state.step >= 3 && (
        <div className={`glass-card ${state.step === 3 ? 'animate-slide-up' : ''}`} style={state.step > 3 ? { opacity: 0.5, height: 60, padding: '15px' } : {}}>
          <h2 className="text-amber" style={{ margin: 0 }}>// STEP 03 — AGRONOMIST ENGINE {state.step > 3 && '✅'}</h2>
          
          {state.step === 3 && (
            <div style={{ marginTop: 30 }}>
              <p>Enter local soil test parameters to generate a targeted fertilizer prescription for <b>{state.prediction?.crop?.toUpperCase()}</b>.</p>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 20, marginTop: 30 }}>
                {[
                  { id: 'n', label: 'Nitrogen (N)', unit: 'kg/ha', bound: '0-140' },
                  { id: 'p', label: 'Phosphorus (P)', unit: 'kg/ha', bound: '5-145' },
                  { id: 'k', label: 'Potassium (K)', unit: 'kg/ha', bound: '5-200' },
                  { id: 'ph', label: 'Soil pH', unit: '', bound: '3.5-9.9' }
                ].map(f => (
                  <div key={f.id} style={{ background: 'rgba(0,0,0,0.4)', padding: 20, borderRadius: 8 }}>
                    <div style={{ fontSize: 14, color: 'var(--accent-amber)', textTransform: 'uppercase', marginBottom: 10 }}>{f.label}</div>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <input 
                        type="number" 
                        value={state.soil[f.id]}
                        onChange={e => setState(s => ({ ...s, soil: { ...s.soil, [f.id]: e.target.value } }))}
                        className="mono"
                        style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '2px solid #444', color: '#fff', fontSize: 24, padding: '5px 0', outline: 'none' }}
                      />
                      <span className="mono" style={{ color: '#888', marginLeft: 10 }}>{f.unit}</span>
                    </div>
                    <div className="mono" style={{ fontSize: 11, color: '#666', marginTop: 10 }}>Range: {f.bound}</div>
                  </div>
                ))}
              </div>

              <div className="mono" style={{ background: 'rgba(255,255,255,0.05)', padding: 15, marginTop: 20, fontSize: 13, borderLeft: '2px solid #666' }}>
                ℹ These values come from your soil test kit or agricultural lab.<br/>They vary field-by-field and season-by-season.
              </div>

              {errorMessage && (
                <div className="mono" style={{ background: 'rgba(255,68,68,0.1)', color: 'var(--accent-red)', padding: 15, borderLeft: '2px solid var(--accent-red)', marginTop: 20 }}>
                  ⚠️ Error: {errorMessage}
                </div>
              )}

              <button 
                className="btn-primary" 
                onClick={handleGeneratePrescription} 
                style={{ marginTop: 30 }}
                disabled={!state.soil.n || !state.soil.p || !state.soil.k || !state.soil.ph}
              >
                [ GENERATE PRESCRIPTION ]
              </button>
            </div>
          )}
        </div>
      )}

      {/* STEP 4 */}
      {state.step === 4 && (
        <div className="glass-card animate-slide-up">
          <h2 style={{ color: '#fff', margin: 0 }}>// STEP 04 — MISSION REPORT</h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 2fr) minmax(300px, 1fr)', gap: 40, marginTop: 30 }}>
            
            {/* Left Col: Tables & Prescription */}
            <div>
              <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 40 }} className="mono">
                <thead>
                  <tr style={{ background: 'rgba(255,255,255,0.1)', textAlign: 'left' }}>
                    <th style={{ padding: 15 }}>Nutrient</th>
                    <th style={{ padding: 15 }}>Your Soil</th>
                    <th style={{ padding: 15 }}>Ideal</th>
                    <th style={{ padding: 15 }}>Gap</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { l: 'Nitrogen (N)', id: 'n', backendId: 'N' },
                    { l: 'Phosphorus (P)', id: 'p', backendId: 'P' },
                    { l: 'Potassium (K)', id: 'k', backendId: 'K' },
                    { l: 'Soil pH', id: 'ph', backendId: 'ph' }
                  ].map(r => {
                    const uVal = parseFloat(state.soil[r.id.toLowerCase()]);
                    const iVal = state.prescription.ideal[r.backendId];
                    const gap = state.prescription.deltas[r.backendId];
                    const isOptimal = Math.abs(gap) < 2 || (r.id === 'ph' && Math.abs(gap) < 0.3);
                    
                    return (
                      <tr key={r.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', backgroundColor: isOptimal ? 'rgba(168,255,62,0.05)' : 'rgba(255,184,0,0.05)' }}>
                        <td style={{ padding: 15 }}>{r.l}</td>
                        <td style={{ padding: 15 }}>{uVal.toFixed(1)}</td>
                        <td style={{ padding: 15 }}>{iVal.toFixed(1)}</td>
                        <td style={{ padding: 15, color: isOptimal ? 'var(--accent-lime)' : 'var(--accent-amber)' }}>
                          {gap > 0 ? '+' : ''}{gap.toFixed(1)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              <div className="mono" style={{ background: '#000', border: '1px solid var(--accent-lime)', borderRadius: 4, padding: 20 }}>
                <div style={{ color: 'var(--accent-lime)', marginBottom: 20, fontSize: 16 }}>
                  🧪 FERTILIZER PRESCRIPTION FOR {state.prediction.crop?.toUpperCase()}
                </div>
                <div style={{ borderTop: '1px dashed #333', borderBottom: '1px dashed #333', padding: '20px 0', lineHeight: 1.8 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: 10, marginBottom: 15 }}>
                    <div style={{ color: '#888' }}>Nitrogen :</div>
                    <div>{state.prescription.prescription.nitrogen.message}</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: 10, marginBottom: 15 }}>
                    <div style={{ color: '#888' }}>Phosphorus:</div>
                    <div>{state.prescription.prescription.phosphorus.message}</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: 10, marginBottom: 15 }}>
                    <div style={{ color: '#888' }}>Potassium :</div>
                    <div>{state.prescription.prescription.potassium.message}</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: 10 }}>
                    <div style={{ color: '#888' }}>pH Adj.   :</div>
                    <div>{state.prescription.prescription.ph.message}</div>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 20, marginTop: 30 }}>
                <button className="btn-primary" onClick={downloadKMLFile} style={{ flex: 1, borderColor: '#fff', color: '#fff' }}>
                  [ 📄 DOWNLOAD KML ]
                </button>
                <button className="btn-primary" onClick={copyReport} style={{ flex: 1, borderColor: '#fff', color: '#fff' }}>
                  [ 📋 COPY REPORT ]
                </button>
              </div>
            </div>

            {/* Right Col: 3D Radar */}
            <div>
               <div style={{ background: 'rgba(0,0,0,0.5)', padding: 20, borderRadius: 8, textAlign: 'center' }}>
                  <div className="mono" style={{ fontSize: 14, marginBottom: 15 }}>
                    <span style={{ color: 'var(--accent-cyan)' }}>■ Your Soil</span>
                    <span style={{ color: 'var(--accent-lime)', marginLeft: 20 }}>■ Ideal Soil</span>
                  </div>
                  <RadarChart3D 
                    userSoil={{n: parseFloat(state.soil.n), p: parseFloat(state.soil.p), k: parseFloat(state.soil.k), ph: parseFloat(state.soil.ph)}} 
                    idealSoil={{n: state.prescription.ideal.N, p: state.prescription.ideal.P, k: state.prescription.ideal.K, ph: state.prescription.ideal.ph}} 
                  />
               </div>
            </div>
            
          </div>
        </div>
      )}

    </div>
  );
}
