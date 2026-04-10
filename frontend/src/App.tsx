import { useState } from "react";
import { BrowserRouter, Navigate, Routes, Route, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Sidebar from "./components/Sidebar.tsx";
import Topbar from "./components/Topbar.tsx";

import Landing from "./pages/Landing";
import Monitor from "./pages/Monitor.tsx";
import Intrusion from "./pages/Intrusion.tsx";
import Loitering from "./pages/Loitering.tsx";
import Crowd from "./pages/Crowd.tsx";
import Weapons from "./pages/Weapons.tsx";
import Alerts from "./pages/Alerts.tsx";
import Analytics from "./pages/Analytics.tsx";
import Reports from "./pages/Reports.tsx";
import Login from "./pages/Login.tsx";
import Signup from "./pages/Signup.tsx";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 1000,
    },
  },
});

import { CameraStreamProvider } from "./context/CameraStreamContext.tsx";

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
      {showShell && <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((c) => !c)} />}
      {showShell && <Topbar collapsed={sidebarCollapsed} />}
      <main
        className={
          showShell
            ? "mt-14 p-5 min-h-[calc(100vh-56px)] page-transition app-shell-bg text-textPrimary"
            : "min-h-screen page-transition app-shell-bg text-textPrimary"
        }
        style={showShell ? { marginLeft: sidebarCollapsed ? 72 : 226 } : undefined}
      >
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/dashboard" element={<Navigate to="/monitor" replace />} />
          <Route
            path="/monitor"
            element={
              <ProtectedRoute>
                <Monitor />
              </ProtectedRoute>
            }
          />
          <Route
            path="/intrusion"
            element={
              <ProtectedRoute>
                <Intrusion />
              </ProtectedRoute>
            }
          />
          <Route
            path="/loitering"
            element={
              <ProtectedRoute>
                <Loitering />
              </ProtectedRoute>
            }
          />
          <Route
            path="/crowd"
            element={
              <ProtectedRoute>
                <Crowd />
              </ProtectedRoute>
            }
          />
          <Route
            path="/weapons"
            element={
              <ProtectedRoute>
                <Weapons />
              </ProtectedRoute>
            }
          />
          <Route
            path="/alerts"
            element={
              <ProtectedRoute>
                <Alerts />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics"
            element={
              <ProtectedRoute>
                <Analytics />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <ProtectedRoute>
                <Reports />
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
