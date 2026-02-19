import type { Metadata } from 'next'
import { Space_Mono, Bebas_Neue } from 'next/font/google'
import './globals.css'

const spaceMono = Space_Mono({ 
  weight: ['400', '700'],
  subsets: ['latin'],
  variable: '--font-mono'
})

const bebasNeue = Bebas_Neue({ 
  weight: '400',
  subsets: ['latin'],
  variable: '--font-display'
})

export const metadata: Metadata = {
  title: 'BetaView - AI Climbing Coach',
  description: 'Analyze your climbing technique with computer vision',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${spaceMono.variable} ${bebasNeue.variable}`}>
        <main className="min-h-screen">
          {children}
        </main>
      </body>
    </html>
  )
}
