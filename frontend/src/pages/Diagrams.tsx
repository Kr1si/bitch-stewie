import { DrawIoEmbed } from "react-drawio";

export default function Diagrams() {
  return (
    <section style={{ height: "100%" }}>
      <h2>Diagrams</h2>
      {/* Self-hosted drawio from docker-compose; LikeC4 exports land here (Phase 4/5). */}
      <div style={{ height: "80vh" }}>
        <DrawIoEmbed baseUrl="http://localhost:8080" />
      </div>
    </section>
  );
}
