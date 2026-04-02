import { useState } from "react";
import { BrowserRouter, Navigate, Routes, Route, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";

import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import Intrusion from "./pages/Intrusion";
import Loitering from "./pages/Loitering";
import Crowd from "./pages/Crowd";
import Alerts from "./pages/Alerts";
import Analytics from "./pages/Analytics";
import Login from "./pages/Login";
import Signup from "./pages/Signup";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 1000,
    },
  },
});

import { CameraStreamProvider } from "./context/CameraStreamContext";

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function AppLayout() {
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const isLanding = location.pathname === "/";
  const isLogin = location.pathname === "/login";
  const isSignup = location.pathname === "/signup";
  const showShell = !isLanding && !isLogin && !isSignup;

  return (
    <>
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((c) => !c)} />
      {showShell && <Topbar collapsed={sidebarCollapsed} />}
      <main
        className={showShell ? "mt-14 p-5 min-h-[calc(100vh-56px)] transition-all duration-300" : ""}
        style={showShell ? { marginLeft: sidebarCollapsed ? 68 : 220 } : undefined}
      >
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="/intrusion" element={<Intrusion />} />
          <Route path="/loitering" element={<Loitering />} />
          <Route path="/crowd" element={<Crowd />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route
            path="/analytics"
            element={
              <ProtectedRoute>
                <Analytics />
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
        </Routes>
      </main>
    </>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <CameraStreamProvider>
          <BrowserRouter>
            <AppLayout />
          </BrowserRouter>
        </CameraStreamProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
