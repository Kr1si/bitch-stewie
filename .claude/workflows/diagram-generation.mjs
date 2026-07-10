export const meta = {
  name: 'diagram-generation',
  description: 'Analyze a codebase/architecture and produce Mermaid diagrams (C4, ERD, sequence, component) + an HTML viewer',
  phases: [
    { title: 'Map', detail: 'parallel Explore agents map structure, data, control-flow, deps' },
    { title: 'Synthesize', detail: 'one agent turns the maps into Mermaid diagrams' },
    { title: 'Render', detail: 'emit a self-contained Mermaid-CDN HTML viewer' },
  ],
}

// args: { target: "./backend", kinds: ["c4","erd","sequence","component"], out: "docs/diagrams/backend.md", useGraphify: false }
// Defaults applied below. `args` is the object passed via Workflow({args:{...}}).

const target = (args && args.target) || '.'
const kinds = (args && args.kinds) || ['c4', 'erd', 'sequence', 'component']
const out = (args && args.out) || 'docs/diagrams/architecture.md'
const useGraphify = !!(args && args.useGraphify)

log(`Generating diagrams for ${target} | kinds: ${kinds.join(', ')} | out: ${out} | graphify: ${useGraphify}`)

// ---- Phase 1: Map (barrier — synth needs all four maps together) ----
phase('Map')

const MAP_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['summary', 'entities'],
  properties: {
    summary: { type: 'string', description: 'markdown bullet list of findings for this aspect' },
    entities: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['name', 'kind', 'relates'],
        properties: {
          name: { type: 'string' },
          kind: { type: 'string', description: 'module | service | table | component | endpoint | actor | datastore' },
          relates: { type: 'array', items: { type: 'string' }, description: 'names this entity depends on or calls' },
          note: { type: 'string' },
        },
      },
    },
  },
}

const mapThunks = [
  () => agent(
    `You are mapping STRUCTURE & ENTRY POINTS of the codebase at "${target}".
Use Glob/Grep/Read (and Bash only if needed). Identify: top-level modules/dirs, entry points
(main, app, index, server bootstrap), service boundaries, and the high-level component tree.
Return a concise markdown summary plus an entities list (kind: module|service|component).`,
    { label: 'map:structure', phase: 'Map', schema: MAP_SCHEMA, agentType: 'Explore' }
  ),
  () => agent(
    `You are mapping DATA MODELS & RELATIONSHIPS of the codebase at "${target}".
Find: DB schemas, ORM models, migrations, type/entity definitions, repositories. Capture each
table/entity, its fields (if obvious), and its relationships (FKs, joins, owns/refs). These feed
an ERD diagram. Return a markdown summary plus entities (kind: table|datastore|entity).`,
    { label: 'map:data', phase: 'Map', schema: MAP_SCHEMA, agentType: 'Explore' }
  ),
  () => agent(
    `You are mapping CONTROL-FLOW / KEY REQUEST PATHS of the codebase at "${target}".
Trace 2-3 representative end-to-end flows (e.g. an HTTP request → handler → service → data layer →
response; or a CLI command path; or a background job). Identify the actors/components involved and
the ordered steps between them. These feed sequence diagrams. Return a markdown summary plus
entities (kind: actor|service|endpoint|component) with relates showing the call chain.`,
    { label: 'map:flow', phase: 'Map', schema: MAP_SCHEMA, agentType: 'Explore' }
  ),
  () => agent(
    `You are mapping EXTERNAL DEPENDENCIES & INTEGRATIONS of the codebase at "${target}".
Find: external APIs, third-party services, message brokers, caches, databases, MCP servers,
deployment targets, and any outbound integrations. Identify the system boundary (what's inside
vs outside). These feed a C4 context diagram. Return a markdown summary plus entities
(kind: service|datastore|actor) with relates pointing to internal components they touch.${
      useGraphify
        ? `\n\nOPTIONAL: if the \`graphify\` CLI is available, you may run \`graphify "${target}" --no-viz\` then \`graphify query "key entities and relationships"\` and fold the result into your summary. Skip silently if it fails or is slow.`
        : ''
    }`,
    { label: 'map:deps', phase: 'Map', schema: MAP_SCHEMA, agentType: 'Explore' }
  ),
]

const maps = (await parallel(mapThunks)).filter(Boolean)
const [structure, data, flow, deps] = maps

if (!maps.length || maps.filter(Boolean).length === 0) {
  log('All mappers returned nothing — aborting.')
  return { ok: false, reason: 'mappers returned empty', out }
}

const mapsBlob = JSON.stringify({ structure, data, flow, deps }, null, 2)

// ---- Phase 2: Synthesize (one agent writes the Mermaid diagrams) ----
phase('Synthesize')

const kindDefs = {
  c4: `C4 diagrams: a **C4 Context** diagram (system + external actors/systems) and a **C4 Container**
diagram (major deployable units inside the system). Use C4-PlantUML-style Mermaid or plain flowchart
with clear grouping.`,
  erd: `An **ERD** (entity-relationship) diagram using \`erDiagram\` for the data models/tables and their relationships.`,
  sequence: `1-2 **sequence diagrams** using \`sequenceDiagram\` for the representative request/control-flow paths.`,
  component: `A **component diagram** using \`flowchart\` with subgraphs for the internal module/component structure.`,
}

const wantedBlocks = kinds.map((k) => `- ${k}: ${kindDefs[k] || '(custom — infer from the maps)'}`).join('\n')

const synth = await agent(
  `You are a software architect producing architecture diagrams as Mermaid from a codebase analysis.

TARGET: ${target}
OUTPUT FILE: ${out}  (write the full document here using the Write tool; create parent dirs first via Bash: \`mkdir -p\`)

Produce a markdown document with:
1. A short title + one-paragraph architecture overview.
2. The following Mermaid diagram sections (each in a \`\`\`mermaid fenced block with a short explanation after):
${wantedBlocks}

RULES:
- Use ONLY entities/relationships present in the analysis below — do not invent components.
- Keep diagrams readable: prefer <= ~20 nodes per diagram; group related nodes with subgraphs.
- Use correct Mermaid syntax (C4 via flowchart+subgraphs is safest; erDiagram for ERD; sequenceDiagram for flows).
- After the diagrams, add a "## Entities" section listing every entity referenced (name, kind, one-line).
- After that, add a "## Sources" section noting the analysis was generated by parallel codebase mappers.

ANALYSIS (JSON: structure, data, flow, deps — each has summary + entities[]):
${mapsBlob}

Return a one-paragraph summary of what you wrote and the path.`,
  { label: 'synthesize', phase: 'Synthesize', agentType: 'general-purpose' }
)

// ---- Phase 3: Render (one agent emits a self-contained HTML viewer) ----
phase('Render')

const htmlPath = out.replace(/\.md$/, '') + '.html'
const render = await agent(
  `Create a self-contained HTML viewer for the Mermaid diagrams in "${out}".

Read "${out}", extract every \`\`\`mermaid fenced block (with its heading), and write "${htmlPath}"
(a single .html file using the Write tool) that:
- loads Mermaid from the CDN: \`https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js\`
- initializes \`mermaid.initialize({ startOnLoad: true, theme: 'default' })\`
- renders each diagram in its own <section> with the original heading
- is standalone (no build step, no local deps), basic clean styling, light + readable.

Do NOT run any network install. Just produce the HTML file. Return the html path.`,
  { label: 'render', phase: 'Render', agentType: 'general-purpose' }
)

return {
  ok: true,
  target,
  kinds,
  out,
  html: htmlPath,
  synthesis: synth,
  render,
  mapCounts: {
    structure: structure ? structure.entities.length : 0,
    data: data ? data.entities.length : 0,
    flow: flow ? flow.entities.length : 0,
    deps: deps ? deps.entities.length : 0,
  },
}