import * as Sentry from "@sentry/nuxt";

Sentry.init({
  dsn: "https://f006fbefe9f09f276721befb2ad93442@o4511298895216640.ingest.us.sentry.io/4511298948825088",

  integrations: [
    Sentry.feedbackIntegration({
      // Control options here
      autoInject: false, // Prevents the default floating button from appearing
      showBranding: false,
      colorScheme: "dark",
      buttonLabel: "Enviar Feedback",
      submitButtonLabel: "Enviar",
      formTitle: "Reportar Bug ou Feedback",
    }),
  ],

  tracesSampleRate: 1.0,
  enableLogs: true,
  sendDefaultPii: true,
  debug: false,
});
