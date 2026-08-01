import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StatCard from "../StatCard";

describe("StatCard", () => {
  it("renders the label and value", () => {
    render(<StatCard icon={<span>ico</span>} label="Runs" value={42} />);
    expect(screen.getByText("Runs")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders an optional subtitle", () => {
    render(<StatCard icon={<span>ico</span>} label="Runs" value={1} sub="today" />);
    expect(screen.getByText("today")).toBeInTheDocument();
  });

  it("does not render a subtitle when none is provided", () => {
    render(<StatCard icon={<span>ico</span>} label="Runs" value={1} />);
    expect(screen.queryByText("today")).not.toBeInTheDocument();
  });
});
