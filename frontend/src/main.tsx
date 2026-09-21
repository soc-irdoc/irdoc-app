import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from './App'
import './styles/global.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      {/*
        react-router-dom v7's BrowserRouter defaults to wrapping every
        location update in React.startTransition() (useTransitions defaults
        to true). Under React 18, a transition-wrapped update can be starved
        indefinitely by ongoing synchronous re-renders elsewhere in the tree
        (e.g. zustand/websocket-driven updates), so history.pushState /
        replaceState changes the URL but <Routes> never re-renders to match —
        exactly the "URL changes, screen doesn't" symptom. Opt out so route
        changes apply as a normal, synchronous state update.
      */}
      <BrowserRouter useTransitions={false}>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
)
