# Presentation

This slide deck covers the educational content for the first 30 minutes of the workshop: the AI Development Lifecycle (ADLC) and Opportunities, Risks & Mitigation.

Use the arrow buttons or keyboard arrow keys to navigate between slides.

---

<div class="slide-viewer" id="slideViewer">
  <div class="slide-progress">
    <span class="slide-counter" id="slideCounter">1 / 16</span>
    <div class="slide-progress-bar"><div class="slide-progress-fill" id="progressFill"></div></div>
  </div>

  <div class="slides-container" id="slidesContainer">

    <!-- ── SECTION 1: ADLC ── -->

    <div class="slide slide-section-header active">
      <div class="slide-content">
        <div class="slide-section-label">Section 1</div>
        <h1>AI Development Lifecycle</h1>
        <p class="slide-subtitle">Understanding how AI systems are built, deployed, and maintained</p>
      </div>
    </div>

    <div class="slide">
      <div class="slide-content">
        <h2>What is the ADLC?</h2>
        <p>The AI Development Lifecycle (ADLC) describes the end-to-end process for designing, building, and operating AI systems responsibly.</p>
        <ul>
          <li>Structured approach to AI system development</li>
          <li>Incorporates governance and ethics at every phase</li>
          <li>Enables repeatable, auditable workflows</li>
        </ul>
        <div class="slide-note">📝 <em>Placeholder — add ADLC definition and diagram here</em></div>
      </div>
    </div>

    <div class="slide">
      <div class="slide-content">
        <h2>Phase 1: Problem Definition</h2>
        <ul>
          <li>Identify business need and success criteria</li>
          <li>Assess feasibility and data availability</li>
          <li>Define scope, constraints, and stakeholders</li>
          <li>Conduct ethical impact assessment</li>
        </ul>
        <div class="slide-note">📝 <em>Placeholder — expand with ADLC Phase 1 detail</em></div>
      </div>
    </div>

    <div class="slide">
      <div class="slide-content">
        <h2>Phase 2: Data Collection & Preparation</h2>
        <ul>
          <li>Identify and gather relevant data sources</li>
          <li>Clean, label, and validate data</li>
          <li>Address bias and representativeness</li>
          <li>Establish data governance and lineage</li>
        </ul>
        <div class="slide-note">📝 <em>Placeholder — expand with ADLC Phase 2 detail</em></div>
      </div>
    </div>

    <div class="slide">
      <div class="slide-content">
        <h2>Phase 3: Model Development</h2>
        <ul>
          <li>Select model architecture and approach</li>
          <li>Train, fine-tune, or prompt-engineer</li>
          <li>Evaluate performance and safety metrics</li>
          <li>Iterate based on results</li>
        </ul>
        <div class="slide-note">📝 <em>Placeholder — expand with ADLC Phase 3 detail</em></div>
      </div>
    </div>

    <div class="slide">
      <div class="slide-content">
        <h2>Phase 4: Deployment & Integration</h2>
        <ul>
          <li>Package and serve the model</li>
          <li>Integrate with existing systems and workflows</li>
          <li>Set up monitoring and alerting</li>
          <li>Define rollback and incident response plans</li>
        </ul>
        <div class="slide-note">📝 <em>Placeholder — expand with ADLC Phase 4 detail</em></div>
      </div>
    </div>

    <div class="slide">
      <div class="slide-content">
        <h2>Phase 5: Operations & Governance</h2>
        <ul>
          <li>Monitor model performance over time</li>
          <li>Detect and address drift and degradation</li>
          <li>Maintain audit trails and documentation</li>
          <li>Periodic re-evaluation and retraining</li>
        </ul>
        <div class="slide-note">📝 <em>Placeholder — expand with ADLC Phase 5 detail</em></div>
      </div>
    </div>

    <div class="slide">
      <div class="slide-content">
        <h2>ADLC for Agents</h2>
        <p>Agent-based systems introduce additional considerations across the lifecycle:</p>
        <ul>
          <li><strong>Tool access</strong> — what can the agent do?</li>
          <li><strong>Autonomy level</strong> — when does it act without human approval?</li>
          <li><strong>Memory & state</strong> — what persists across sessions?</li>
          <li><strong>Observability</strong> — can you explain what the agent did and why?</li>
        </ul>
        <div class="slide-note">📝 <em>Placeholder — add agent-specific ADLC considerations</em></div>
      </div>
    </div>

    <!-- ── SECTION 2: OPPORTUNITIES, RISKS & MITIGATION ── -->

    <div class="slide slide-section-header">
      <div class="slide-content">
        <div class="slide-section-label">Section 2</div>
        <h1>Opportunities, Risks & Mitigation</h1>
        <p class="slide-subtitle">Making informed decisions about where and how to deploy AI agents</p>
      </div>
    </div>

    <div class="slide">
      <div class="slide-content">
        <h2>Opportunities</h2>
        <p>AI agents can unlock significant value when applied thoughtfully:</p>
        <ul>
          <li>Automate repetitive, well-defined tasks at scale</li>
          <li>Augment human decision-making with richer context</li>
          <li>Enable 24/7 responsiveness across systems</li>
          <li>Synthesize information across disparate sources</li>
        </ul>
        <div class="slide-note">📝 <em>Placeholder — add industry-specific opportunity examples</em></div>
      </div>
    </div>

    <div class="slide">
      <div class="slide-content">
        <h2>Risk Categories</h2>
        <ul>
          <li>⚠️ <strong>Safety</strong> — unintended actions in production systems</li>
          <li>🔒 <strong>Security</strong> — prompt injection, data exfiltration</li>
          <li>⚖️ <strong>Fairness</strong> — amplifying bias in automated decisions</li>
          <li>🔍 <strong>Transparency</strong> — inability to explain agent behavior</li>
          <li>📜 <strong>Compliance</strong> — regulatory and legal exposure</li>
        </ul>
        <div class="slide-note">📝 <em>Placeholder — add risk examples from ADLC content</em></div>
      </div>
    </div>

    <div class="slide">
      <div class="slide-content">
        <h2>Security Risks in Depth</h2>
        <ul>
          <li><strong>Prompt injection</strong> — malicious input hijacks agent behavior</li>
          <li><strong>Tool misuse</strong> — agent is tricked into calling dangerous tools</li>
          <li><strong>Data leakage</strong> — sensitive context exposed in completions</li>
          <li><strong>Privilege escalation</strong> — agent gains unintended permissions</li>
        </ul>
        <div class="slide-note">📝 <em>Placeholder — add real-world examples and attack scenarios</em></div>
      </div>
    </div>

    <div class="slide">
      <div class="slide-content">
        <h2>Mitigation Strategies</h2>
        <ul>
          <li>✅ Apply least-privilege to all tool access</li>
          <li>✅ Validate and sanitize all inputs before processing</li>
          <li>✅ Require human-in-the-loop for high-stakes actions</li>
          <li>✅ Log all agent decisions with full context</li>
          <li>✅ Test adversarially before deployment</li>
        </ul>
        <div class="slide-note">📝 <em>Placeholder — map mitigations to specific risk categories</em></div>
      </div>
    </div>

    <div class="slide">
      <div class="slide-content">
        <h2>Responsible Agent Design Principles</h2>
        <ul>
          <li><strong>Transparency</strong> — document what the agent can and cannot do</li>
          <li><strong>Controllability</strong> — ensure humans can override or stop the agent</li>
          <li><strong>Accountability</strong> — every action must be attributable and logged</li>
          <li><strong>Robustness</strong> — degrade gracefully under adversarial conditions</li>
        </ul>
        <div class="slide-note">📝 <em>Placeholder — tie back to IBM trustworthy AI framework</em></div>
      </div>
    </div>

    <div class="slide slide-section-header">
      <div class="slide-content">
        <div class="slide-section-label">Up Next</div>
        <h1>Let's Build</h1>
        <p class="slide-subtitle">Time for hands-on labs. Head to <strong>Lab 1: Naive Agent Implementation</strong> to get started.</p>
        <p><a href="../lab-1/" class="slide-cta">Go to Lab 1 →</a></p>
      </div>
    </div>

  </div><!-- /slides-container -->

  <div class="slide-nav">
    <button class="slide-btn" id="prevBtn" onclick="changeSlide(-1)" disabled>&#8592; Prev</button>
    <button class="slide-btn" id="nextBtn" onclick="changeSlide(1)">Next &#8594;</button>
  </div>
</div>

<style>
.slide-viewer {
  font-family: 'IBM Plex Sans', sans-serif;
  border: 1px solid var(--md-default-fg-color--lightest);
  border-radius: 8px;
  overflow: hidden;
  margin: 1.5rem 0;
}

.slide-progress {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.6rem 1.2rem;
  background: var(--md-default-fg-color--lightest);
  font-size: 0.8rem;
  color: var(--md-default-fg-color--light);
}

.slide-progress-bar {
  flex: 1;
  height: 4px;
  background: var(--md-default-fg-color--lighter);
  border-radius: 2px;
  overflow: hidden;
}

.slide-progress-fill {
  height: 100%;
  background: var(--md-primary-fg-color);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.slides-container {
  position: relative;
  min-height: 340px;
}

.slide {
  display: none;
  padding: 2.5rem 3rem;
  animation: fadeIn 0.25s ease;
}

.slide.active {
  display: block;
}

.slide-section-header {
  background: var(--md-primary-fg-color);
  color: var(--md-primary-bg-color);
  min-height: 340px;
  display: none;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.slide-section-header.active {
  display: flex;
}

.slide-section-header .slide-content {
  max-width: 600px;
}

.slide-section-header h1,
.slide-section-header p {
  color: var(--md-primary-bg-color);
}

.slide-section-label {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  opacity: 0.75;
  margin-bottom: 0.5rem;
}

.slide-subtitle {
  font-size: 1.1rem;
  opacity: 0.9;
  margin-top: 0.75rem;
}

.slide h2 {
  margin-top: 0;
  border-bottom: 2px solid var(--md-primary-fg-color);
  padding-bottom: 0.5rem;
}

.slide ul {
  line-height: 1.9;
}

.slide-note {
  margin-top: 1.5rem;
  padding: 0.6rem 1rem;
  background: var(--md-admonition-bg-color, var(--md-default-fg-color--lightest));
  border-left: 3px solid var(--md-accent-fg-color, #ffd);
  border-radius: 4px;
  font-size: 0.875rem;
  color: var(--md-default-fg-color--light);
}

.slide-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.2rem;
  background: var(--md-default-fg-color--lightest);
  border-top: 1px solid var(--md-default-fg-color--lighter);
}

.slide-btn {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.875rem;
  padding: 0.4rem 1rem;
  border: 1px solid var(--md-primary-fg-color);
  background: transparent;
  color: var(--md-primary-fg-color);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.slide-btn:hover:not(:disabled) {
  background: var(--md-primary-fg-color);
  color: var(--md-primary-bg-color);
}

.slide-btn:disabled {
  opacity: 0.35;
  cursor: default;
  border-color: var(--md-default-fg-color--lighter);
  color: var(--md-default-fg-color--lighter);
}

.slide-cta {
  display: inline-block;
  margin-top: 1.5rem;
  padding: 0.6rem 1.4rem;
  background: var(--md-primary-bg-color);
  color: var(--md-primary-fg-color) !important;
  border-radius: 4px;
  font-weight: 600;
  text-decoration: none;
}

.slide-cta:hover {
  opacity: 0.85;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>

<script>
(function() {
  var current = 0;
  var container = document.getElementById('slidesContainer');
  var slides = container ? container.querySelectorAll('.slide') : [];
  var total = slides.length;

  function updateUI() {
    var counter = document.getElementById('slideCounter');
    var fill = document.getElementById('progressFill');
    var prev = document.getElementById('prevBtn');
    var next = document.getElementById('nextBtn');
    if (counter) counter.textContent = (current + 1) + ' / ' + total;
    if (fill) fill.style.width = ((current + 1) / total * 100) + '%';
    if (prev) prev.disabled = current === 0;
    if (next) next.disabled = current === total - 1;
  }

  window.changeSlide = function(dir) {
    if (!slides.length) return;
    slides[current].classList.remove('active');
    current = Math.max(0, Math.min(total - 1, current + dir));
    slides[current].classList.add('active');
    updateUI();
  };

  document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') changeSlide(1);
    if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   changeSlide(-1);
  });

  updateUI();
})();
</script>
