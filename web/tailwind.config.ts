import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

export default {
	darkMode: ["class"],
	content: [
		"./pages/**/*.{ts,tsx}",
		"./components/**/*.{ts,tsx}",
		"./app/**/*.{ts,tsx}",
		"./src/**/*.{ts,tsx}",
	],
	prefix: "",
	theme: {
		container: {
			center: true,
			padding: '2rem',
			screens: {
				'2xl': '1400px'
			}
		},
		extend: {
			fontFamily: {
				sans: ['Inter', 'system-ui', 'sans-serif'],
				display: ['Rajdhani', 'Inter', 'sans-serif'],
				mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
			},
			colors: {
				border: 'hsl(var(--border))',
				input: 'hsl(var(--input))',
				ring: 'hsl(var(--ring))',
				background: 'hsl(var(--background))',
				foreground: 'hsl(var(--foreground))',
				void: 'hsl(var(--void))',
				primary: {
					DEFAULT: 'hsl(var(--primary))',
					foreground: 'hsl(var(--primary-foreground))',
					glow: 'hsl(var(--primary-glow))'
				},
				accent: {
					DEFAULT: 'hsl(var(--accent))',
					foreground: 'hsl(var(--accent-foreground))'
				},
				secondary: {
					DEFAULT: 'hsl(var(--secondary))',
					foreground: 'hsl(var(--secondary-foreground))'
				},
				muted: {
					DEFAULT: 'hsl(var(--muted))',
					foreground: 'hsl(var(--muted-foreground))'
				},
				subtle: {
					DEFAULT: 'hsl(var(--subtle))'
				},
				destructive: {
					DEFAULT: 'hsl(var(--destructive))',
					foreground: 'hsl(var(--destructive-foreground))',
					bright: 'hsl(var(--danger-bright))'
				},
				card: {
					DEFAULT: 'hsl(var(--card))',
					foreground: 'hsl(var(--card-foreground))'
				},
				popover: {
					DEFAULT: 'hsl(var(--popover))',
					foreground: 'hsl(var(--popover-foreground))'
				},
				surface: {
					DEFAULT: 'hsl(var(--surface))',
					raised: 'hsl(var(--surface-raised))',
					high: 'hsl(var(--surface-high))'
				},
				success: {
					DEFAULT: 'hsl(var(--success))',
					bright: 'hsl(var(--success-bright))',
					foreground: 'hsl(var(--success-foreground))'
				},
				warning: {
					DEFAULT: 'hsl(var(--warning))',
					bright: 'hsl(var(--warning-bright))',
					foreground: 'hsl(var(--warning-foreground))'
				},
				info: {
					DEFAULT: 'hsl(var(--info))'
				},
				violet: {
					DEFAULT: 'hsl(var(--violet))',
					bright: 'hsl(var(--violet-bright))'
				},
				hud: {
					line: 'var(--hud-line)',
					'soft': 'var(--hud-line-soft)',
					'strong': 'var(--hud-line-strong)',
					glow: 'var(--hud-glow)',
					'glow-strong': 'var(--hud-glow-strong)',
					surface: 'var(--hud-surface)',
					'raised': 'var(--hud-surface-raised)'
				},
				sidebar: {
					DEFAULT: 'hsl(var(--void))',
					foreground: 'hsl(var(--foreground))',
					primary: 'hsl(var(--primary))',
					'primary-foreground': 'hsl(var(--primary-foreground))',
					accent: 'hsl(var(--surface-high))',
					'accent-foreground': 'hsl(var(--foreground))',
					border: 'hsl(var(--border))',
					ring: 'hsl(var(--ring))'
				}
			},
			borderRadius: {
				lg: 'var(--radius)',
				md: 'calc(var(--radius) - 3px)',
				sm: 'calc(var(--radius) - 5px)'
			},
			spacing: {
				'rail': 'var(--rail-width)',
				'sidebar': 'var(--sidebar-width)',
				'frame': 'var(--frame-height)'
			},
			boxShadow: {
				panel: '0 24px 52px -34px rgba(0,0,0,0.95), inset 0 1px 0 var(--hud-inset)',
				'glow-xs': '0 0 0 1px var(--hud-glow)',
				'glow-sm': '0 0 20px -8px var(--hud-glow-strong)',
				glow: '0 0 34px -12px var(--hud-glow-strong), 0 0 0 1px var(--hud-glow)',
				'glow-lg': '0 0 80px -20px var(--hud-glow-strong)',
				'inset-hud': 'inset 0 0 44px -24px var(--hud-glow-strong)',
				online: '0 0 18px -6px hsl(var(--success) / 0.75)',
				waiting: '0 0 18px -6px hsl(var(--warning) / 0.75)',
				danger: '0 0 18px -6px hsl(var(--danger) / 0.75)',
				violet: '0 0 20px -8px hsl(var(--violet) / 0.7)'
			},
			backgroundImage: {
				'signature': 'linear-gradient(115deg, hsl(var(--accent)) 0%, hsl(var(--primary)) 46%, hsl(var(--primary-glow)) 100%)',
				'panel-sheen': 'linear-gradient(180deg, hsl(var(--primary) / 0.07), transparent 42%)',
				'violet-sheen': 'linear-gradient(115deg, hsl(var(--violet)) 0%, hsl(var(--violet-bright)) 100%)',
				'rail-fade': 'linear-gradient(180deg, hsl(var(--void) / 0.6), transparent)'
			},
			transitionTimingFunction: {
				hud: 'cubic-bezier(0.22, 1, 0.36, 1)'
			},
			transitionDuration: {
				'150': '150ms',
				'220': '220ms',
				'300': '300ms'
			},
			keyframes: {
				'accordion-down': {
					from: { height: '0' },
					to: { height: 'var(--radix-accordion-content-height)' }
				},
				'accordion-up': {
					from: { height: 'var(--radix-accordion-content-height)' },
					to: { height: '0' }
				}
			},
			animation: {
				'accordion-down': 'accordion-down 0.2s ease-out',
				'accordion-up': 'accordion-up 0.2s ease-out',
				'breathe': 'luma-breathe 5.5s ease-in-out infinite',
				'orbit': 'luma-orbit 26s linear infinite',
				'orbit-slow': 'luma-orbit 52s linear infinite',
				'orbit-reverse': 'luma-orbit-reverse 36s linear infinite',
				'spin-slow': 'luma-spin-slow 18s linear infinite',
				'ring': 'luma-ring 2.8s ease-out infinite',
				'ring-slow': 'luma-ring 4.6s ease-out infinite',
				'sweep': 'luma-sweep 4.6s linear infinite',
				'shimmer': 'luma-shimmer 2.6s linear infinite',
				'fade-up': 'luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) both',
				'fade-in': 'luma-fade-in 0.4s ease-out both',
				'slide-right': 'luma-slide-right 0.45s cubic-bezier(0.22,1,0.36,1) both',
				'scale-in': 'luma-scale-in 0.45s cubic-bezier(0.22,1,0.36,1) both',
				'pulse-dot': 'luma-pulse-dot 2.2s ease-out infinite',
				'wave': 'luma-wave 1.1s ease-in-out infinite',
				'float': 'luma-float 6.5s ease-in-out infinite',
				'blink': 'luma-blink 2.2s step-end infinite',
				'dash': 'luma-dash 24s linear infinite'
			}
		}
	},
	plugins: [tailwindcssAnimate],
} satisfies Config;
