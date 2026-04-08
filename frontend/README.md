# Harness Lab Workbench

这个前端目录现在只服务 Harness Lab 研究工作台，不再承载旧工作流编辑器或旧控制台心智。

## Stack

- React 18
- TypeScript
- Vite
- Ant Design
- Tailwind CSS

## Current structure

```text
src/
├── App.tsx
├── main.tsx
├── index.css
└── lab/
    ├── api.ts
    ├── types.ts
    └── components/
```

## Commands

```bash
npm install
npm run dev
npm run build
npm run lint
npm test
```

## Product surface

- Sessions
- Constraints
- Context
- Prompts
- Runs
- Replays
- Policies
- Experiments
- Settings

## Notes

- The workbench talks to the FastAPI control plane on `http://localhost:4600`.
- The UI is intentionally research-centric and trace-oriented.
- Legacy workflow-editor concepts are out of scope for this frontend.
