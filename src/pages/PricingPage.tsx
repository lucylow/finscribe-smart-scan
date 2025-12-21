import Header from "@/components/Header";
import Pricing from "@/components/Pricing";
import Footer from "@/components/Footer";

const PricingPage = () => {
  return (
    <div className="min-h-screen">
      <Header />
      <main>
        <div className="min-h-screen bg-gray-50 py-20 px-6">
          <Pricing />
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default PricingPage;


