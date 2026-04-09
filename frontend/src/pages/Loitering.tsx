import { Navigate } from "react-router-dom";

export default function Loitering() {
  return <Navigate to="/monitor?module=loitering" replace />;
}
