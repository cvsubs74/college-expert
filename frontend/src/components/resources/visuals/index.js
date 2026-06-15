// Single registry the paper renderer uses to resolve {component: 'Foo'} references.
// Avoids dynamic imports — the visuals are small enough that bundling them
// together is cheaper than the round-trip cost of code-splitting per paper.

import HiddenCostHero from './HiddenCostHero';
import ResearchTimeBar from './ResearchTimeBar';
import BeforeAfterGrid from './BeforeAfterGrid';
import ResolverFlow from './ResolverFlow';
import TemplateMatrix from './TemplateMatrix';
import TranslationDiagram from './TranslationDiagram';
import AgentBridgeFlow from './AgentBridgeFlow';
import ToolSurfaceGrid from './ToolSurfaceGrid';
import ClosedLoopDiagram from './ClosedLoopDiagram';

export const visualRegistry = {
    HiddenCostHero,
    ResearchTimeBar,
    BeforeAfterGrid,
    ResolverFlow,
    TemplateMatrix,
    TranslationDiagram,
    AgentBridgeFlow,
    ToolSurfaceGrid,
    ClosedLoopDiagram,
};

export const getVisual = (name) => visualRegistry[name] || null;
