import { Toaster } from "@/components/ui/sonner"
import { AppShell } from "@/components/AppShell"
import { AlertCenter } from "@/pages/AlertCenter"
import { Advisory } from "@/pages/Advisory"
import { Dashboard } from "@/pages/Dashboard"
import { Farm } from "@/pages/Farm"
import { ForgotPassword } from "@/pages/ForgotPassword"
import { Forecast } from "@/pages/Forecast"
import { Help } from "@/pages/Help"
import { Landing } from "@/pages/Landing"
import { Login } from "@/pages/Login"
import { Onboarding } from "@/pages/Onboarding"
import { PlotAnalytics } from "@/pages/PlotAnalytics"
import { PlotDetail } from "@/pages/PlotDetail"
import { Profile } from "@/pages/Profile"
import { Register } from "@/pages/Register"
import { ResetPassword } from "@/pages/ResetPassword"
import { Search } from "@/pages/Search"
import { Settings } from "@/pages/Settings"
import { Route, Routes } from "react-router-dom"

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/onboarding" element={<Onboarding />} />

        <Route path="/dashboard" element={<AppShell><Dashboard /></AppShell>} />
        <Route path="/alerts" element={<AppShell><AlertCenter /></AppShell>} />
        <Route path="/forecast" element={<AppShell><Forecast /></AppShell>} />
        <Route path="/advisory" element={<AppShell><Advisory /></AppShell>} />
        <Route path="/farm" element={<AppShell><Farm /></AppShell>} />
        <Route path="/plots/:plotId" element={<AppShell><PlotDetail /></AppShell>} />
        <Route path="/plots/:plotId/analytics" element={<AppShell><PlotAnalytics /></AppShell>} />
        <Route path="/profile" element={<AppShell><Profile /></AppShell>} />
        <Route path="/settings" element={<AppShell><Settings /></AppShell>} />
        <Route path="/help" element={<AppShell><Help /></AppShell>} />
        <Route path="/search" element={<AppShell><Search /></AppShell>} />
      </Routes>
      <Toaster />
    </>
  )
}

export default App
