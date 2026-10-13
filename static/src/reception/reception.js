/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ReceptionApp extends Component {
 static template = "yt_reception.App";
 setup() {
  this.orm = useService("orm");
  this.notification = useService("notification");
  this.action = useService("action");
  this.state = useState({busy:false,partner:0,vehicle:0,customers:[],vehicles:[],makes:[],models:[],branches:[],advisors:[],orders:[],order:null,form:this.blank(),showCar:false,car:{},complaints:[""],requests:[],photos:[],error:"",unsaved:false,previewPhoto:0});
  onWillStart(async()=>{await this.loadChoices();});
 }
 blank(){return {odometer_in:0,odometer_out:0,arrival_at:new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,16),branch_id:false,advisor_id:false,reception_notes:"",internal_notes:"",customer_source:"",work_source:"",no_parts_needed:false,warranty:false,intake_method:"branch"};}
 get selectedPartner(){return this.state.customers.find(x=>x.id===this.state.partner);}
 get selectedVehicle(){return this.state.vehicles.find(x=>x.id===this.state.vehicle);}
 async loadChoices(){
  try {
   const [customers,makes,models,branches,advisors,orders] = await Promise.all([
    this.orm.searchRead("res.partner",[["name","!=",false]],["name","mobile","phone","email"],{limit:250}),
    this.orm.searchRead("yt.reception.make",[],["name"],{limit:250}),
    this.orm.searchRead("yt.reception.model",[],["name","make_id"],{limit:400}),
    this.orm.searchRead("res.company",[],["name"],{limit:100}),
    this.orm.searchRead("res.users",[["share","=",false]],["name"],{limit:100}),
    this.orm.searchRead("yt.reception.order",[],["name","partner_id","vehicle_id","state"],{limit:50,order:"id desc"})]);
   Object.assign(this.state,{customers,makes,models,branches,advisors,orders});
  }catch(e){this.fail(e);}
 }
 fail(e){this.state.error=e?.message||String(e);this.notification.add(this.state.error,{type:"danger"});}
 changed(){this.state.unsaved=true;}
 async customerChange(ev){
  if(this.state.unsaved && !window.confirm("تغيير العميل سيلغي بيانات السيارة غير المحفوظة. هل تريد المتابعة؟")){ev.target.value=this.state.partner;return;}
  this.state.partner=Number(ev.target.value)||0;this.state.vehicle=0;this.state.vehicles=[];this.state.unsaved=false;
  if(this.state.partner)await this.loadVehicles();
 }
 async loadVehicles(){
  this.state.vehicles=await this.orm.searchRead("yt.reception.vehicle",[["partner_id","=",this.state.partner]],["plate","plate_country","make_id","model_id","vin","engine_number","year","gear","odometer","color","plate_type","plate_condition"],{limit:250});
 }
 async createCar(){
  if(!this.state.partner){this.notification.add("اختر العميل أولاً",{type:"warning"});return;}
  this.state.car={partner_id:this.state.partner,plate_country:"SA",plate_type:"private",plate_condition:"good",make_id:false,model_id:false,year:new Date().getFullYear(),gear:"auto",plate:"",vin:"",engine_number:"",color:"",odometer:0};
  this.state.showCar=true;
 }
 carField(k,ev){this.state.car[k]=ev.target.type==="number"?Number(ev.target.value):ev.target.value;this.changed();}
 async submitCar(){
  if(!this.state.car.plate?.trim()){this.notification.add("رقم اللوحة مطلوب",{type:"warning"});return;}
  this.state.busy=true;
  try{
   const v={...this.state.car};
   for(const field of ["make_id","model_id"])v[field]=v[field]?Number(v[field]):false;
   const ids=await this.orm.create("yt.reception.vehicle",[v]);
   await this.loadVehicles();this.state.vehicle=ids[0];this.state.showCar=false;this.notification.add("تم تسجيل السيارة",{type:"success"});
  }catch(e){this.fail(e);}finally{this.state.busy=false;}
 }
 update(k,ev){this.state.form[k]=ev.target.type==="checkbox"?ev.target.checked:ev.target.type==="number"?Number(ev.target.value):["branch_id","advisor_id"].includes(k)?Number(ev.target.value)||false:ev.target.value;this.changed();}
 async save(){
  if(!this.state.partner||!this.state.vehicle){this.notification.add("العميل والسيارة مطلوبان",{type:"warning"});return;}
  this.state.busy=true;
  try{
   const clean=a=>a.map(x=>x.trim()).filter(Boolean);
   const values={...this.state.form};
   if(values.arrival_at){const local=new Date(values.arrival_at.replace(" ","T").replace(/Z$/,""));if(!Number.isNaN(local.getTime()))values.arrival_at=local.toISOString().slice(0,19).replace("T"," ");}
   if(this.state.complaints.some(x=>!x.trim())||this.state.requests.some(x=>!x.trim()))throw new Error("أكمل بنود الشكاوى والخدمات أو احذف الصفوف الفارغة.");
   if(this.state.order){
    this.state.order=await this.orm.call("yt.reception.order","save_reception",[[this.state.order.id],values,clean(this.state.complaints),clean(this.state.requests)]);
   }else{
    const createValues={partner_id:this.state.partner,vehicle_id:this.state.vehicle,...values,complaint_ids:clean(this.state.complaints).map(name=>[0,0,{name}]),request_ids:clean(this.state.requests).map(name=>[0,0,{name}])};
    const ids=await this.orm.create("yt.reception.order",[createValues]);
    await this.open(ids[0]);
   }
   this.state.unsaved=false;this.notification.add("تم حفظ الاستقبال بنجاح",{type:"success"});await this.loadChoices();
  }catch(e){this.fail(e);}finally{this.state.busy=false;}
 }
 async open(id){
  try{
   const o=await this.orm.call("yt.reception.order","get_reception",[[id]]);
   this.state.order=o;this.state.partner=o.partner_id[0];await this.loadVehicles();this.state.vehicle=o.vehicle_id[0];
   this.state.form=Object.fromEntries(Object.keys(this.blank()).map(k=>[k,o[k]??this.blank()[k]]));
   if(o.arrival_at){const d=new Date(o.arrival_at.replace(" ","T")+"Z");this.state.form.arrival_at=new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);}
   this.state.complaints=o.complaints.map(c=>c.name);this.state.requests=o.requests.map(r=>r.name);this.state.photos=o.photos;this.state.unsaved=false;
  }catch(e){this.fail(e);}
 }
 newOrder(){if(this.state.unsaved&&!window.confirm("هناك تغييرات غير محفوظة. هل تريد إلغاءها؟"))return;this.state.order=null;this.state.partner=0;this.state.vehicle=0;this.state.vehicles=[];this.state.form=this.blank();this.state.complaints=[];this.state.requests=[];this.state.photos=[];this.state.unsaved=false;}
 addRow(k){this.state[k].push("");this.changed();}
 removeRow(k,i){this.state[k].splice(i,1);this.changed();}
 row(k,i,ev){this.state[k][i]=ev.target.value;this.changed();}
 async upload(ev){
  const files=Array.from(ev.target.files||[]);
  await this.processFiles(files);
  ev.target.value="";
 }
 async dropPhotos(ev){ev.preventDefault();await this.processFiles(Array.from(ev.dataTransfer?.files||[]));}
 async processFiles(files){if(!this.state.order){this.notification.add("احفظ أمر العمل قبل رفع الصور",{type:"warning"});return;}
  this.state.busy=true;
  try{
   for(const file of files){
    if(!["image/jpeg","image/png"].includes(file.type)||file.size>6*1024*1024)throw new Error("الصور JPG/PNG وبحد أقصى 6 ميجابايت للصورة.");
    const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(String(r.result).split(",")[1]);r.onerror=reject;r.readAsDataURL(file);});
    await this.orm.create("yt.reception.photo",[{order_id:this.state.order.id,name:file.name,data,mimetype:file.type}]);
   }
   await this.open(this.state.order.id);this.notification.add("تم رفع الصور",{type:"success"});
  }catch(e){this.fail(e);}finally{this.state.busy=false;}
 }
 async delPhoto(id){if(!window.confirm("حذف الصورة؟"))return;try{await this.orm.unlink("yt.reception.photo",[id]);await this.open(this.state.order.id);}catch(e){this.fail(e);}}
 async primaryPhoto(id){try{const all=this.state.photos.map(p=>p.id);for(const photoId of all)await this.orm.write("yt.reception.photo",[photoId],{is_primary:photoId===id});await this.open(this.state.order.id);}catch(e){this.fail(e);}}
 phone(){const p=this.selectedPartner;return (p?.mobile||p?.phone||"").replace(/[^+\d]/g,"");}
 call(){const p=this.phone();if(p)window.location.href="tel:"+p;}
 whatsapp(){const p=this.phone().replace(/\D/g,"");if(p)window.open("https://wa.me/"+p,"_blank","noopener,noreferrer");}
 createPartner(){this.action.doAction({type:"ir.actions.act_window",res_model:"res.partner",views:[[false,"form"]],target:"new",context:{default_customer_rank:1}});}
 openPartner(){if(this.state.partner)this.action.doAction({type:"ir.actions.act_window",res_model:"res.partner",res_id:this.state.partner,views:[[false,"form"]],target:"current"});}
 get filteredModels(){return this.state.models.filter(m=>m.make_id?.[0]===Number(this.state.car.make_id));}
}
registry.category("actions").add("yt_workshop_v4.reception_app",ReceptionApp);
